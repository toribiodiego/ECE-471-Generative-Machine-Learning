"""Core MediaLoop class for audio/video streaming.

This module contains the MediaLoop class that coordinates real-time
audio and video capture, streaming to Gemini Live API, and playing
back synthesized audio responses.
"""

import asyncio
import os
from typing import Dict, Any, Optional

import cv2
import numpy as np
import pyaudio
from google.genai import types
from PIL import Image

from src.utils.config_loader import load_config, load_system_instruction
from src.utils.media_processing import encode_image_from_array, resize_frame
from src.utils.gemini_client import get_gemini_client, create_speech_config, get_live_config


# Map mic types to chunk sizes for audio streaming
_CHUNK_MAP = {"dynamic_mic": 512, "computer_mic": 1024}

# Global variable for session resumption
_declared_previous_handle = None


class MediaLoop:
    """Manages the real-time audio/video streaming loop with Gemini Live API.

    This class coordinates multiple async tasks:
    - listen_audio: Captures microphone input and sends to Gemini
    - receive_audio: Receives audio responses from Gemini
    - play_audio: Plays received audio through speakers
    - capture_video: Captures webcam frames and sends to Gemini
    - run: Orchestrates all tasks in an async task group

    Attributes:
        chunk_size: Audio buffer size based on microphone type
        pya: PyAudio instance for audio I/O
        audio_in_queue: Queue for incoming audio from Gemini
        session: Active Gemini Live API session
        quit: Event to signal shutdown
        audio_stream_in: Input audio stream
        audio_stream_out: Output audio stream
        latest_video_frame: Most recent captured video frame
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize MediaLoop with configuration.

        Args:
            config: Configuration dictionary containing audio/video settings
                   and API parameters.

        Raises:
            ValueError: If MIC_TYPE in config is not supported.
        """
        self.config = config
        mic = config.get("MIC_TYPE")
        if mic not in _CHUNK_MAP:
            raise ValueError(f"Invalid MIC_TYPE '{mic}'")
        self.chunk_size = _CHUNK_MAP[mic]
        self.pya = pyaudio.PyAudio()
        self.audio_in_queue = asyncio.Queue()
        self.session = None
        self.quit = asyncio.Event()
        self.audio_stream_in = None
        self.audio_stream_out = None
        self.latest_video_frame = None

    async def listen_audio(self):
        """Capture audio from microphone and stream to Gemini.

        Opens the default input device and continuously reads audio chunks,
        sending them to the Gemini Live API session as realtime input.
        Runs until quit event is set.
        """
        info = self.pya.get_default_input_device_info()
        self.audio_stream_in = await asyncio.to_thread(
            self.pya.open,
            format=self.config["AUDIO_FORMAT"],
            channels=self.config["AUDIO_CHANNELS"],
            rate=self.config["INPUT_SAMPLE_RATE"],
            input=True,
            input_device_index=info["index"],
            frames_per_buffer=self.chunk_size,
        )
        while not self.quit.is_set():
            data = await asyncio.to_thread(
                self.audio_stream_in.read,
                self.chunk_size,
                exception_on_overflow=False,
            )
            if self.session:
                # wrap raw bytes in a Blob for realtime audio
                blob = types.Blob(data=data, mime_type="audio/pcm")
                await self.session.send_realtime_input(audio=blob)
            await asyncio.sleep(0)

    async def receive_audio(self):
        """Receive audio responses from Gemini and queue for playback.

        Listens for messages from the Gemini Live API session, handling
        session resumption updates and queueing audio data for playback.
        Runs until quit event is set.
        """
        global _declared_previous_handle
        while not self.quit.is_set():
            turn = self.session.receive()
            async for msg in turn:
                if msg.session_resumption_update:
                    upd = msg.session_resumption_update
                    if upd.resumable and upd.new_handle:
                        _declared_previous_handle = upd.new_handle
                if msg.data:
                    await self.audio_in_queue.put(msg.data)
            while not self.audio_in_queue.empty():
                _ = self.audio_in_queue.get_nowait()

    async def play_audio(self):
        """Play audio responses through speakers.

        Opens the output audio stream and plays audio chunks received from
        Gemini. Buffers audio to ensure smooth playback. Runs until quit
        event is set, then flushes remaining buffer.
        """
        self.audio_stream_out = await asyncio.to_thread(
            self.pya.open,
            format=self.config["AUDIO_FORMAT"],
            channels=self.config["AUDIO_CHANNELS"],
            rate=self.config["OUTPUT_SAMPLE_RATE"],
            output=True,
        )
        buf = b""
        while not self.quit.is_set():
            try:
                data = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.1)
                buf += data if isinstance(data, (bytes, bytearray)) else data.tobytes()
            except asyncio.TimeoutError:
                pass
            if len(buf) >= self.chunk_size * 4:
                await asyncio.to_thread(self.audio_stream_out.write, buf)
                buf = b""
        if buf:
            await asyncio.to_thread(self.audio_stream_out.write, buf)

    def _capture_frame(self, cap) -> Optional[Image.Image]:
        """Capture and process a single video frame.

        Args:
            cap: OpenCV VideoCapture object.

        Returns:
            PIL Image if frame captured successfully, None otherwise.
        """
        ok, frame = cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        resize_frame(img, tuple(self.config["THUMBNAIL_MAX_SIZE"]))
        return img

    async def capture_video(self):
        """Capture webcam frames and stream to Gemini.

        Opens the default camera and continuously captures frames, resizing
        and encoding them before sending to the Gemini Live API session.
        Stores the latest frame for UI display. Runs until quit event is set.
        """
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        if not cap.isOpened():
            print("Cannot open camera")
            return
        while not self.quit.is_set():
            img = await asyncio.to_thread(self._capture_frame, cap)
            if img and self.session:
                arr = np.array(img)
                img_dict = encode_image_from_array(arr)
                blob = types.Blob(data=img_dict["data"], mime_type=img_dict["mime_type"])
                await self.session.send_realtime_input(video=blob)
                self.latest_video_frame = img
            await asyncio.sleep(self.config["VIDEO_CAPTURE_INTERVAL"])
        cap.release()

    async def run(self, api_key: str):
        """Run the media loop with all streaming tasks.

        Establishes connection to Gemini Live API and spawns async tasks
        for audio input/output and video capture. Coordinates all tasks
        until shutdown is requested.

        Args:
            api_key: Gemini API key for authentication.
        """
        global _declared_previous_handle

        # Get Gemini client and configuration
        client = get_gemini_client(api_key, self.config["GEMINI_HTTP_OPTIONS"])
        instruction = load_system_instruction(self.config)
        speech_config = create_speech_config(self.config["VOICE_NAME"])
        live_cfg = get_live_config(
            system_instruction=instruction,
            response_modalities=self.config["GEMINI_RESPONSE_MODALITIES"],
            speech_config=speech_config,
            previous_handle=_declared_previous_handle,
        )

        # Connect and run all tasks
        async with client.aio.live.connect(
            model=self.config["GEMINI_MODEL"], config=live_cfg
        ) as session, asyncio.TaskGroup() as tg:
            self.session = session
            tg.create_task(self.listen_audio())
            tg.create_task(self.receive_audio())
            tg.create_task(self.play_audio())
            tg.create_task(self.capture_video())
            await self.quit.wait()

    def shutdown(self):
        """Signal all async tasks to stop.

        Sets the quit event, causing all streaming tasks to exit their
        loops and clean up resources.
        """
        self.quit.set()


def get_previous_handle() -> Optional[str]:
    """Get the session resumption handle from the last session.

    Returns:
        Previous session handle or None if no previous session.
    """
    return _declared_previous_handle
