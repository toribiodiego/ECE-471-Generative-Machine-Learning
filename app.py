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


# Gemini API configuration
def load_environment():
    """Load environment variables from the .env file."""
    load_dotenv()


def get_gemini_configuration(api_key: str):
    """
    Create a client and configuration for connecting to the Gemini API.

    Modify this function if you need to adjust Gemini parameters later on.
    """
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    config = {"response_modalities": ["AUDIO"]}
    return client, config


# data encoding helpers
def encode_audio(data: np.ndarray) -> dict:
    """Encode Audio data to send to the server."""
    return {
        "mime_type": "audio/pcm",
        "data": base64.b64encode(data.tobytes()).decode("UTF-8"),
    }


def encode_image(data: np.ndarray) -> dict:
    """Encode image data to a base64 string."""
    with BytesIO() as output_bytes:
        pil_image = Image.fromarray(data)
        pil_image.save(output_bytes, "JPEG")
        bytes_data = output_bytes.getvalue()
    base64_str = base64.b64encode(bytes_data).decode("utf-8")
    return {"mime_type": "image/jpeg", "data": base64_str}


# gemini handler class
class GeminiHandler(AsyncAudioVideoStreamHandler):
    def __init__(
        self, expected_layout="mono", output_sample_rate=24000, output_frame_size=480
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=16000,
        )
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.quit = asyncio.Event()
        self.session = None
        self.last_frame_time = 0

    def copy(self) -> "GeminiHandler":
        """Return a new instance of GeminiHandler with the same configuration."""
        return GeminiHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )

    async def video_receive(self, frame: np.ndarray):
        """Receive video frame, send encoded images to Gemini at most once a second."""
        if self.session:
            if time.time() - self.last_frame_time > 1:
                self.last_frame_time = time.time()
                await self.session.send(encode_image(frame))
                if self.latest_args[2] is not None:
                    await self.session.send(encode_image(self.latest_args[2]))
        self.video_queue.put_nowait(frame)

    async def video_emit(self) -> VideoEmitType:
        return await self.video_queue.get()

    async def connect(self, api_key: str):
        """Establish a connection to the Gemini API using the provided API key."""
        if self.session is None:
            client, config = get_gemini_configuration(api_key)
            async with client.aio.live.connect(
                model="gemini-2.0-flash-exp", config=config
            ) as session:
                self.session = session
                # Start receiving audio responses asynchronously.
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
        """Process incoming audio frames."""
        _, array = frame
        array = array.squeeze()
        audio_message = encode_audio(array)
        if self.session:
            await self.session.send(audio_message)

    async def emit(self) -> AudioEmitType:
        if not self.args_set.is_set():
            await self.wait_for_args()
        if self.session is None:
            # Start connecting if not already done.
            asyncio.create_task(self.connect(self.latest_args[1]))
        array = await self.audio_queue.get()
        return (self.output_sample_rate, array)

    def shutdown(self) -> None:
        self.quit.set()
        self.connection = None
        self.args_set.clear()
        self.quit.clear()


# UI building functions
def build_webrtc_component() -> WebRTC:
    """Build and return the WebRTC component with the appropriate configuration."""
    return WebRTC(
        label="Video Chat",
        modality="audio-video",
        mode="send-receive",
        elem_id="video-source",
        rtc_configuration=get_twilio_turn_credentials(),
        icon="https://www.gstatic.com/lamda/images/gemini_favicon_f069958c85030456e93de685481c559f160ea06b.png",
        pulse_color="rgb(35, 157, 225)",
        icon_button_color="rgb(35, 157, 225)",
    )


def create_ui() -> gr.Blocks:
    """
    Create the Gradio Blocks UI.

    This function separates all UI components from the business logic.
    """
    css = """
    #video-source {max-width: 600px !important; max-height: 600px !important;}
    """
    demo = gr.Blocks(css=css)

    with demo:
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
        with gr.Row() as api_key_row:
            # Pre-populate using GEMINI_API_KEY from environment variables.
            api_key = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="Enter your API Key",
                value=os.getenv("GEMINI_API_KEY"),
            )
        with gr.Row(visible=False) as row:
            with gr.Column():
                webrtc = build_webrtc_component()
            with gr.Column():
                image_input = gr.Image(
                    label="Image", type="numpy", sources=["upload", "clipboard"]
                )
            # Setup the stream using the GeminiHandler.
            webrtc.stream(
                GeminiHandler(),
                inputs=[webrtc, api_key, image_input],
                outputs=[webrtc],
                time_limit=90,
                concurrency_limit=2,
            )
            # toggle visibility of the API key field and UI row on submission.
            api_key.submit(
                lambda: (gr.update(visible=False), gr.update(visible=True)),
                None,
                [api_key_row, row],
            )
    return demo


# main entry point
def main():
    load_environment()
    demo = create_ui()
    demo.launch()


if __name__ == "__main__":
    main()
