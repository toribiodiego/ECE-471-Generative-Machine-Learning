import asyncio
import base64
import os
import time
from io import BytesIO
import threading

import gradio as gr
import numpy as np
from google import genai
from PIL import Image
from dotenv import load_dotenv
import pyaudio
import cv2

# --- Global configuration dictionary ---
config = {
    "GEMINI_MODEL": "gemini-2.0-flash-exp",
    "GEMINI_HTTP_OPTIONS": {"api_version": "v1alpha"},
    "GEMINI_RESPONSE_MODALITIES": ["AUDIO"],
    "INPUT_SAMPLE_RATE": 16000,
    "OUTPUT_SAMPLE_RATE": 24000,
    "CHUNK_SIZE": 1024,
    "WEB_UI_TITLE": "Gemini Audio/Video Demo",
    "VIDEO_CAPTURE_INTERVAL": 0.5,  # seconds between capturing frames
}

# --- Low-level Audio Constants ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
pya = pyaudio.PyAudio()

def load_environment():
    load_dotenv()

def get_gemini_configuration(api_key: str):
    client = genai.Client(api_key=api_key, http_options=config["GEMINI_HTTP_OPTIONS"])
    gemini_config = {"response_modalities": config["GEMINI_RESPONSE_MODALITIES"]}
    return client, gemini_config

def encode_audio(data: bytes) -> dict:
    return {
        "mime_type": "audio/pcm",
        "data": base64.b64encode(data).decode("UTF-8"),
    }

def encode_image_from_array(arr: np.ndarray) -> dict:
    # Encodes a numpy image array as JPEG.
    with BytesIO() as output_bytes:
        Image.fromarray(arr).save(output_bytes, "JPEG")
        bytes_data = output_bytes.getvalue()
    return {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(bytes_data).decode("utf-8"),
    }

def get_blank_image():
    # Returns a simple blank (black) image.
    blank_arr = np.zeros((480, 640, 3), dtype=np.uint8)
    return Image.fromarray(blank_arr)

class MediaLoop:
    """
    Captures and processes both audio and video.
    Audio from the microphone is streamed to Gemini and its response is played back.
    Video is captured continuously from the computer’s camera (via OpenCV), sent to Gemini (if active),
    and stored locally for display.
    """
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.session = None
        self.quit = asyncio.Event()
        self.audio_stream_in = None
        self.audio_stream_out = None
        self.latest_video_frame = None  # Latest captured video frame (PIL Image)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream_in = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=config["INPUT_SAMPLE_RATE"],
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=config["CHUNK_SIZE"],
        )
        kwargs = {"exception_on_overflow": False}
        while not self.quit.is_set():
            data = await asyncio.to_thread(
                self.audio_stream_in.read, config["CHUNK_SIZE"], **kwargs
            )
            if self.session:
                await self.session.send({"data": data, "mime_type": "audio/pcm"})
            await asyncio.sleep(0)

    async def receive_audio(self):
        # Receives Gemini's audio responses and enqueues them for playback.
        while not self.quit.is_set():
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    await self.audio_in_queue.put(data)
            # Clear any leftover audio.
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def play_audio(self):
        self.audio_stream_out = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=config["OUTPUT_SAMPLE_RATE"],
            output=True,
        )
        buffer = b""
        while not self.quit.is_set():
            try:
                data = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.1)
                if isinstance(data, np.ndarray):
                    data = data.tobytes()
                buffer += data
            except asyncio.TimeoutError:
                pass
            if len(buffer) >= config["CHUNK_SIZE"] * 4:
                await asyncio.to_thread(self.audio_stream_out.write, buffer)
                buffer = b""
        if buffer:
            await asyncio.to_thread(self.audio_stream_out.write, buffer)

    def _capture_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        # Convert from BGR to RGB for correct color display.
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        # Optionally, resize or process the image here as needed.
        img.thumbnail((1024, 1024))
        return img

    async def capture_video(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        if not cap.isOpened():
            print("Cannot open camera")
            return
        while not self.quit.is_set():
            img = await asyncio.to_thread(self._capture_frame, cap)
            if img is not None:
                self.latest_video_frame = img
                if self.session:
                    arr = np.array(img)
                    encoded_frame = encode_image_from_array(arr)
                    await self.session.send(encoded_frame)
            await asyncio.sleep(config["VIDEO_CAPTURE_INTERVAL"])
        cap.release()

    async def run(self):
        key = os.getenv("GEMINI_API_KEY")
        client, gemini_config = get_gemini_configuration(key)
        try:
            async with client.aio.live.connect(model=config["GEMINI_MODEL"], config=gemini_config) as session, asyncio.TaskGroup() as tg:
                self.session = session
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                tg.create_task(self.capture_video())
                await self.quit.wait()
        except asyncio.CancelledError:
            pass

    def shutdown(self):
        self.quit.set()

# Global MediaLoop instance and thread placeholders.
media_loop = None
media_loop_thread = None

def run_media_loop(loop_instance):
    asyncio.run(loop_instance.run())

def start_media_session():
    global media_loop, media_loop_thread
    # Reinitialize a new session if none is running or if the previous session has been stopped.
    if media_loop is None or media_loop.quit.is_set():
        media_loop = MediaLoop()
        media_loop_thread = threading.Thread(target=run_media_loop, args=(media_loop,), daemon=True)
        media_loop_thread.start()
        return "Media session started."
    else:
        return "Media session already running."

def stop_media_session():
    global media_loop, media_loop_thread
    if media_loop is not None:
        media_loop.shutdown()
        media_loop = None
        media_loop_thread = None
        return "Media session stopped."
    else:
        return "No active session."

def video_stream():
    """
    Generator function that continuously yields the latest video frame.
    The frame is converted to a NumPy array before being sent so that the Gradio Image component
    displays it correctly. If no frame is available, a blank image is returned.
    """
    while True:
        if media_loop is not None and media_loop.latest_video_frame is not None:
            # Convert PIL image to NumPy array
            frame = np.array(media_loop.latest_video_frame)
        else:
            frame = np.array(get_blank_image())
        yield frame
        time.sleep(config["VIDEO_CAPTURE_INTERVAL"])

def create_ui():
    with gr.Blocks(title=config["WEB_UI_TITLE"]) as demo:
        gr.Markdown(
            "## Gemini Audio/Video Demo\n"
            "Click **Start** to begin a session that captures your microphone audio and camera video. "
            "Gemini will process your audio and respond, and your live video feed will be displayed below. "
            "Click **Stop** to end the session and clear its memory so that a new session will start on the next Start."
        )
        with gr.Row():
            start_btn = gr.Button("Start")
            stop_btn = gr.Button("Stop")
        status = gr.Textbox(label="Status", interactive=False)
        # The gr.Image component streams the live video feed.
        video_feed = gr.Image(label="Live Video Feed", streaming=True, interactive=True)
        start_btn.click(fn=start_media_session, inputs=[], outputs=[status])
        stop_btn.click(fn=stop_media_session, inputs=[], outputs=[status])
        video_feed.stream(fn=video_stream, inputs=[], outputs=[video_feed])
    return demo

def main():
    load_environment()
    demo = create_ui()
    demo.launch()

if __name__ == "__main__":
    main()
