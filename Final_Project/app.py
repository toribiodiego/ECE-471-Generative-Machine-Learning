import asyncio
import base64
import os
import time
from io import BytesIO
import threading
import yaml

import gradio as gr
import numpy as np
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv
import pyaudio
import cv2

# ─── Load & merge configs ─────────────────────────────────────────────
def load_config():
    with open("config.yaml", 'r') as f:
        dev_cfg = yaml.safe_load(f)
    with open("media.yaml", 'r') as f:
        media_cfg = yaml.safe_load(f)
    return {**media_cfg, **dev_cfg}

config = load_config()

# ─── Session Resumption Handle ─────────────────────────────────────────
declared_previous_handle = None  # for session resumption

# ─── Map mic types to chunk sizes ──────────────────────────────────────
_CHUNK_MAP = {"dynamic_mic": 512, "computer_mic": 1024}

# ─── Load environment (for GEMINI_API_KEY) ────────────────────────────
load_dotenv()

def load_system_instruction() -> str:
    fn = config.get("INSTRUCTIONS_FILE")
    if os.path.isfile(fn):
        text = open(fn, encoding="utf-8").read().strip()
        if text:
            return text
    raise FileNotFoundError(f"Missing or empty instructions file '{fn}'")

def get_gemini_configuration(api_key: str):
    global declared_previous_handle
    client = genai.Client(api_key=api_key, http_options=config["GEMINI_HTTP_OPTIONS"])
    instruction = load_system_instruction()
    live_cfg = types.LiveConnectConfig(
        response_modalities=config["GEMINI_RESPONSE_MODALITIES"],
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
        session_resumption=types.SessionResumptionConfig(
            handle=declared_previous_handle
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=instruction)],
            role="user",
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config["VOICE_NAME"])
            )
        ),
    )
    return client, live_cfg

def encode_image_from_array(arr: np.ndarray) -> dict:
    with BytesIO() as out:
        Image.fromarray(arr).save(out, "JPEG")
        return {"mime_type": "image/jpeg", "data": out.getvalue()}

def get_blank_image() -> Image.Image:
    h, w, _ = config["BLANK_IMAGE_DIMS"]
    return Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8))

class MediaLoop:
    def __init__(self):
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
        info = self.pya.get_default_input_device_info()
        self.audio_stream_in = await asyncio.to_thread(
            self.pya.open,
            format=config["AUDIO_FORMAT"],
            channels=config["AUDIO_CHANNELS"],
            rate=config["INPUT_SAMPLE_RATE"],
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
        global declared_previous_handle
        while not self.quit.is_set():
            turn = self.session.receive()
            async for msg in turn:
                if msg.session_resumption_update:
                    upd = msg.session_resumption_update
                    if upd.resumable and upd.new_handle:
                        declared_previous_handle = upd.new_handle
                if msg.data:
                    await self.audio_in_queue.put(msg.data)
            while not self.audio_in_queue.empty():
                _ = self.audio_in_queue.get_nowait()

    async def play_audio(self):
        self.audio_stream_out = await asyncio.to_thread(
            self.pya.open,
            format=config["AUDIO_FORMAT"],
            channels=config["AUDIO_CHANNELS"],
            rate=config["OUTPUT_SAMPLE_RATE"],
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

    def _capture_frame(self, cap):
        ok, frame = cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.thumbnail(config["THUMBNAIL_MAX_SIZE"])
        return img

    async def capture_video(self):
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
            await asyncio.sleep(config["VIDEO_CAPTURE_INTERVAL"])
        cap.release()

    async def run(self):
        key = os.getenv("GEMINI_API_KEY")
        client, cfg = get_gemini_configuration(key)
        async with client.aio.live.connect(
            model=config["GEMINI_MODEL"], config=cfg
        ) as session, asyncio.TaskGroup() as tg:
            self.session = session
            tg.create_task(self.listen_audio())
            tg.create_task(self.receive_audio())
            tg.create_task(self.play_audio())
            tg.create_task(self.capture_video())
            await self.quit.wait()

    def shutdown(self):
        self.quit.set()

# ─── Media Loop Control ─────────────────────────────────────────────────
media_loop = None
media_loop_thread = None

def run_media_loop(loop: MediaLoop):
    asyncio.run(loop.run())

# ─── Session Control ───────────────────────────────────────────────────
def start_media_session() -> str:
    global media_loop, media_loop_thread
    if media_loop is None or media_loop.quit.is_set():
        media_loop = MediaLoop()
        media_loop_thread = threading.Thread(
            target=run_media_loop, args=(media_loop,), daemon=True
        )
        media_loop_thread.start()
    return "Started"

def stop_media_session() -> str:
    global media_loop, media_loop_thread
    if media_loop:
        media_loop.shutdown()
        media_loop = None
        media_loop_thread = None
    return "Stopped"

# ─── Gradio UI ─────────────────────────────────────────────────────────
def create_ui():
    with gr.Blocks(title=config["WEB_UI_TITLE"]) as demo:
        gr.Markdown(
            "## Gemini Audio/Video Demo\n"
            "Click **Start** to open the session; **Stop** to end."
        )
        with gr.Row():
            btn_start = gr.Button("Start")
            btn_stop = gr.Button("Stop")
        status = gr.Textbox(label="Status", interactive=False)
        live = gr.Video(
            label="Live Video Feed",
            sources=["webcam"],
            streaming=True,
            autoplay=True,
        )
        btn_start.click(start_media_session, [], status)
        btn_stop.click(stop_media_session, [], status)
    return demo

# ─── Entry Point ───────────────────────────────────────────────────────
def main():
    demo = create_ui()
    demo.launch()

if __name__ == "__main__":
    main()
