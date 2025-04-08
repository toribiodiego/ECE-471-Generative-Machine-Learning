import asyncio
import base64
import os
import time
from io import BytesIO

import gradio as gr
import numpy as np
from google import genai
from gradio_webrtc import (
    AsyncAudioVideoStreamHandler,
    WebRTC,
    async_aggregate_bytes_to_16bit,
    VideoEmitType,
    AudioEmitType,
    get_twilio_turn_credentials,
)
from PIL import Image
from dotenv import load_dotenv

config = {
    "GEMINI_MODEL": "gemini-2.0-flash-exp",
    "GEMINI_HTTP_OPTIONS": {"api_version": "v1alpha"},
    "GEMINI_RESPONSE_MODALITIES": ["AUDIO"],
    "INPUT_SAMPLE_RATE": 16000,
    "EXPECTED_LAYOUT": "mono",
    "OUTPUT_SAMPLE_RATE": 24000,
    "OUTPUT_FRAME_SIZE": 480,
    "WEBRTC_LABEL": "Video Chat",
    "WEBRTC_MODALITY": "audio-video",
    "WEBRTC_MODE": "send-receive",
    "WEBRTC_ELEM_ID": "video-source",
    "WEBRTC_ICON": "https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png",
    "WEBRTC_PULSE_COLOR": "rgb(35, 157, 225)",
    "WEBRTC_ICON_BUTTON_COLOR": "rgb(35, 157, 225)",
    "VIDEO_SOURCE_MAX_WIDTH": "600px",
    "VIDEO_SOURCE_MAX_HEIGHT": "600px",
    "STREAM_TIME_LIMIT": 90,
    "STREAM_CONCURRENCY_LIMIT": 2,
}


def load_environment():
    load_dotenv()


def get_gemini_configuration(api_key: str):
    client = genai.Client(api_key=api_key, http_options=config["GEMINI_HTTP_OPTIONS"])
    gemini_config = {"response_modalities": config["GEMINI_RESPONSE_MODALITIES"]}
    return client, gemini_config


def encode_audio(data: np.ndarray) -> dict:
    return {
        "mime_type": "audio/pcm",
        "data": base64.b64encode(data.tobytes()).decode("UTF-8"),
    }


def encode_image(data: np.ndarray) -> dict:
    with BytesIO() as output_bytes:
        Image.fromarray(data).save(output_bytes, "JPEG")
        bytes_data = output_bytes.getvalue()
    base64_str = base64.b64encode(bytes_data).decode("utf-8")
    return {"mime_type": "image/jpeg", "data": base64_str}


class GeminiHandler(AsyncAudioVideoStreamHandler):
    def __init__(self) -> None:
        super().__init__(
            config["EXPECTED_LAYOUT"],
            config["OUTPUT_SAMPLE_RATE"],
            config["OUTPUT_FRAME_SIZE"],
            input_sample_rate=config["INPUT_SAMPLE_RATE"],
        )
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.quit = asyncio.Event()
        self.session = None
        self.last_frame_time = 0

    def copy(self) -> "GeminiHandler":
        return GeminiHandler()

    async def video_receive(self, frame: np.ndarray):
        if self.session:
            if time.time() - self.last_frame_time > 1:
                self.last_frame_time = time.time()
                await self.session.send(encode_image(frame))
                if len(self.latest_args) > 1 and self.latest_args[1] is not None:
                    await self.session.send(encode_image(self.latest_args[1]))
        self.video_queue.put_nowait(frame)

    async def video_emit(self) -> VideoEmitType:
        return await self.video_queue.get()

    async def connect(self):
        if self.session is None:
            key = os.getenv("GEMINI_API_KEY")
            client, gemini_config = get_gemini_configuration(key)
            async with client.aio.live.connect(
                model=config["GEMINI_MODEL"], config=gemini_config
            ) as session:
                self.session = session
                asyncio.create_task(self.receive_audio())
                await self.quit.wait()

    async def generator(self):
        while not self.quit.is_set():
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    yield data

    async def receive_audio(self):
        async for audio_response in async_aggregate_bytes_to_16bit(self.generator()):
            self.audio_queue.put_nowait(audio_response)

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        _, array = frame
        audio_message = encode_audio(array.squeeze())
        if self.session:
            await self.session.send(audio_message)

    async def emit(self) -> AudioEmitType:
        if not self.args_set.is_set():
            await self.wait_for_args()
        if self.session is None:
            asyncio.create_task(self.connect())
        array = await self.audio_queue.get()
        return (self.output_sample_rate, array)

    def shutdown(self) -> None:
        self.quit.set()
        self.connection = None
        self.args_set.clear()
        self.quit.clear()


def build_webrtc_component() -> WebRTC:
    return WebRTC(
        label=config["WEBRTC_LABEL"],
        modality=config["WEBRTC_MODALITY"],
        mode=config["WEBRTC_MODE"],
        elem_id=config["WEBRTC_ELEM_ID"],
        rtc_configuration=get_twilio_turn_credentials(),
        icon=config["WEBRTC_ICON"],
        pulse_color=config["WEBRTC_PULSE_COLOR"],
        icon_button_color=config["WEBRTC_ICON_BUTTON_COLOR"],
    )


def create_ui() -> gr.Blocks:
    css = (
        f"#video-source {{max-width: {config['VIDEO_SOURCE_MAX_WIDTH']} !important; "
        f"max-height: {config['VIDEO_SOURCE_MAX_HEIGHT']} !important;}}"
    )
    demo = gr.Blocks(css=css)
    with demo:
        # Directly setting the HTML info inline
        gr.HTML(
            """
            <div style='display: flex; align-items: center; justify-content: center; gap: 20px'>
                <div style="background-color: var(--block-background-fill); border-radius: 8px">
                    <img src="https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png" style="width: 100px; height: 100px;">
                </div>
                <div>
                    <h1>INFO: gradio_webrtc's new home is FastRTC. Use demo <a href="https://huggingface.co/spaces/fastrtc/gemini-audio-video" target="_blank">here</a></h1>
                    <h1>Gen AI SDK Voice Chat</h1>
                    <p>Speak with Gemini using real-time audio + video streaming</p>
                    <p>Powered by <a href="https://gradio.app/">Gradio</a> and <a href="https://freddyaboulton.github.io/gradio-webrtc/">WebRTC</a>⚡️</p>
                    <p>Get an API Key <a href="https://support.google.com/googleapi/answer/6158862?hl=en">here</a></p>
                </div>
            </div>
            """
        )
        with gr.Row() as row:
            with gr.Column():
                webrtc = build_webrtc_component()
            with gr.Column():
                image_input = gr.Image(
                    label="Image", type="numpy", sources=["upload", "clipboard"]
                )
            webrtc.stream(
                GeminiHandler(),
                inputs=[webrtc, image_input],
                outputs=[webrtc],
                time_limit=config["STREAM_TIME_LIMIT"],
                concurrency_limit=config["STREAM_CONCURRENCY_LIMIT"],
            )
    return demo


def main():
    load_environment()
    demo = create_ui()
    demo.launch()


if __name__ == "__main__":
    main()
