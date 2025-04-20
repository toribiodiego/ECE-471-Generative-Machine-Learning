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
    # common development settings
    with open("config.yaml", 'r') as f:
        dev_cfg = yaml.safe_load(f)
    # media / runtime parameters
    with open("media.yaml", 'r') as f:
        media_cfg = yaml.safe_load(f)
    # merge, letting dev_cfg override if keys collide
    return {**media_cfg, **dev_cfg}

config = load_config()


# ─── Map mic types to chunk sizes ──────────────────────────────────────
_CHUNK_MAP = {
    "dynamic_mic": 512,     # e.g. external dynamic microphone
    "computer_mic": 1024,   # built‑in computer microphone
}


# ─── Load environment (for GEMINI_API_KEY) ────────────────────────────
load_dotenv()


def load_system_instruction() -> str:
    fn = config["INSTRUCTIONS_FILE"]
    if os.path.isfile(fn):
        text = open(fn, encoding="utf-8").read().strip()
        if text:
            return text
    raise FileNotFoundError(f"Missing or empty instructions file '{fn}'")


def get_gemini_configuration(api_key: str):
    client = genai.Client(api_key=api_key, http_options=config["GEMINI_HTTP_OPTIONS"])
    instruction = load_system_instruction()
    live_cfg = types.LiveConnectConfig(
        response_modalities=config["GEMINI_RESPONSE_MODALITIES"],
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


def encode_text(text: str) -> dict:
    return {"mime_type": "text/plain", "data": base64.b64encode(text.encode()).decode()}


def encode_audio(data: bytes) -> dict:
    return {"mime_type": "audio/pcm", "data": base64.b64encode(data).decode()}


def encode_image_from_array(arr: np.ndarray) -> dict:
    with BytesIO() as out:
        Image.fromarray(arr).save(out, "JPEG")
        return {"mime_type": "image/jpeg", "data": base64.b64encode(out.getvalue()).decode()}


def get_blank_image() -> Image.Image:
    h, w, _ = config["BLANK_IMAGE_DIMS"]
    return Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8))


class MediaLoop:
    def __init__(self):
        mic = config.get("MIC_TYPE")
        if mic not in _CHUNK_MAP:
            raise ValueError(
                f"Invalid MIC_TYPE '{mic}'. Must be one of: {', '.join(_CHUNK_MAP.keys())}"
            )
        self.chunk_size = _CHUNK_MAP[mic]

        # initialize PyAudio
        self.pya = pyaudio.PyAudio()
        self.audio_in_queue   = asyncio.Queue()
        self.session          = None
        self.quit             = asyncio.Event()
        self.audio_stream_in  = None
        self.audio_stream_out = None
        self.latest_video_frame = None

    async def listen_audio(self):
        mic_info = self.pya.get_default_input_device_info()
        self.audio_stream_in = await asyncio.to_thread(
            self.pya.open,
            format=config["AUDIO_FORMAT"],
            channels=config["AUDIO_CHANNELS"],
            rate=config["INPUT_SAMPLE_RATE"],
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=self.chunk_size,
        )
        kwargs = {"exception_on_overflow": False}
        while not self.quit.is_set():
            data = await asyncio.to_thread(
                self.audio_stream_in.read, self.chunk_size, **kwargs
            )
            if self.session:
                await self.session.send({"data": data, "mime_type": "audio/pcm"})
            await asyncio.sleep(0)

    async def receive_audio(self):
        while not self.quit.is_set():
            turn = self.session.receive()
            async for resp in turn:
                if resp.data:
                    await self.audio_in_queue.put(resp.data)
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    async def play_audio(self):
        self.audio_stream_out = await asyncio.to_thread(
            self.pya.open,
            format=config["AUDIO_FORMAT"],
            channels=config["AUDIO_CHANNELS"],
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

            if len(buffer) >= self.chunk_size * 4:
                await asyncio.to_thread(self.audio_stream_out.write, buffer)
                buffer = b""
        if buffer:
            await asyncio.to_thread(self.audio_stream_out.write, buffer)

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
            if img:
                self.latest_video_frame = img
                if self.session:
                    arr = np.array(img)
                    await self.session.send(encode_image_from_array(arr))
            await asyncio.sleep(config["VIDEO_CAPTURE_INTERVAL"])
        cap.release()

    async def run(self):
        key = os.getenv("GEMINI_API_KEY")
        client, live_cfg = get_gemini_configuration(key)
        try:
            async with client.aio.live.connect(
                model=config["GEMINI_MODEL"], config=live_cfg
            ) as session, asyncio.TaskGroup() as tg:
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


def video_stream():
    while True:
        if media_loop and media_loop.latest_video_frame:
            yield np.array(media_loop.latest_video_frame)
        else:
            yield np.array(get_blank_image())
        time.sleep(config["VIDEO_CAPTURE_INTERVAL"])


# ─── Gradio UI ────────────────────────────────────────────────────────
def create_ui():
    with gr.Blocks(title=config["WEB_UI_TITLE"]) as demo:
        gr.Markdown(
            "## Gemini Audio/Video Demo\n"
            "Click **Start** to open the mic session; you'll see your webcam feed below. "
            "Click **Stop** to end."
        )
        with gr.Row():
            btn_start = gr.Button("Start")
            btn_stop  = gr.Button("Stop")

        status = gr.Textbox(label="Status", interactive=False)

        # Always visible so browser requests camera access up front:
        live_video = gr.Video(
            label="Live Video Feed",
            sources=["webcam"],
            streaming=True,
            autoplay=True,
        )

        btn_start.click(fn=start_media_session, inputs=[], outputs=[status])
        btn_stop .click(fn=stop_media_session,  inputs=[], outputs=[status])

    return demo


def main():
    demo = create_ui()
    demo.launch()


if __name__ == "__main__":
    main()
