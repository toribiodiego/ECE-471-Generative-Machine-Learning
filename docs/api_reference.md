[Documentation Index](README.md) > API Reference

# API Reference

This document provides comprehensive API documentation for all public functions and classes in the Agnus multimodal agent application.

## Table of Contents

- [Main Entry Point](#main-entry-point)
- [Configuration Utilities](#configuration-utilities)
- [Media Processing Utilities](#media-processing-utilities)
- [Gemini Client Utilities](#gemini-client-utilities)
- [Core MediaLoop](#core-medialoop)
- [Session Manager](#session-manager)
- [UI Interface](#ui-interface)

---

## Main Entry Point

### `src.app`

Main application entry point for launching the Gradio web interface.

#### `main()`

Launch the Gradio web application.

**Description**: Parses command-line arguments and starts the Gradio interface with the specified configuration.

**Returns**: None

**Example**:
```bash
# Run with default settings
python -m src.app

# Run on custom port with public link
python -m src.app --port 8080 --share

# Run with debug logging
python -m src.app --debug
```

#### `parse_args()`

Parse command-line arguments.

**Returns**: `argparse.Namespace` - Parsed command-line arguments

**Available Arguments**:
- `--port`: Port to run the Gradio server on (default: 7860)
- `--share`: Create a public shareable link (flag)
- `--debug`: Enable debug mode with verbose logging (flag)

---

## Configuration Utilities

### `src.utils.config_loader`

Functions for loading and managing YAML configuration files.

#### `load_config(config_path="src/config/config.yaml", media_path="src/config/media.yaml")`

Load and merge YAML configuration files.

**Description**: Loads both config.yaml (development settings) and media.yaml (runtime A/V parameters), merging them into a single configuration dictionary. Values from config.yaml take precedence over media.yaml in case of duplicate keys.

**Parameters**:
- `config_path` (str, optional): Path to the main config YAML file. Defaults to "src/config/config.yaml"
- `media_path` (str, optional): Path to the media config YAML file. Defaults to "src/config/media.yaml"

**Returns**: `Dict[str, Any]` - Merged configuration dictionary containing all settings

**Raises**:
- `FileNotFoundError`: If either configuration file does not exist
- `yaml.YAMLError`: If configuration files contain invalid YAML

**Example**:
```python
from src.utils.config_loader import load_config

# Load with default paths
config = load_config()
print(config["GEMINI_MODEL"])  # gemini-2.0-flash-live-001
print(config["INPUT_SAMPLE_RATE"])  # 16000

# Load with custom paths
config = load_config(
    config_path="custom/config.yaml",
    media_path="custom/media.yaml"
)
```

#### `load_system_instruction(config)`

Load system instruction text from file.

**Description**: Reads the system instruction file path from config and loads the instruction text that defines the agent's personality and behavior.

**Parameters**:
- `config` (Dict[str, Any]): Configuration dictionary containing INSTRUCTIONS_FILE key

**Returns**: `str` - System instruction text content

**Raises**:
- `FileNotFoundError`: If instruction file is missing or empty
- `KeyError`: If INSTRUCTIONS_FILE key is not in config

**Example**:
```python
from src.utils.config_loader import load_config, load_system_instruction

config = load_config()
instructions = load_system_instruction(config)
print(f"Loaded {len(instructions)} characters of instructions")
```

#### `get_config_value(config, key, default=None)`

Safely retrieve a configuration value with optional default.

**Parameters**:
- `config` (Dict[str, Any]): Configuration dictionary
- `key` (str): Configuration key to retrieve
- `default` (Any, optional): Default value to return if key is not found. Defaults to None

**Returns**: `Any` - Configuration value for the key, or default if key not found

**Example**:
```python
from src.utils.config_loader import load_config, get_config_value

config = load_config()

# Get value with default
mic_type = get_config_value(config, "MIC_TYPE", "computer_mic")
print(mic_type)  # dynamic_mic

# Missing key returns default
timeout = get_config_value(config, "TIMEOUT", 30)
print(timeout)  # 30
```

---

## Media Processing Utilities

### `src.utils.media_processing`

Functions for image and audio transformations.

#### `encode_image_from_array(arr)`

Convert a numpy array to a JPEG-encoded blob.

**Description**: Takes a numpy array representing an image and encodes it as a JPEG in memory, returning a dictionary with MIME type and binary data suitable for streaming to the Gemini API.

**Parameters**:
- `arr` (np.ndarray): Numpy array representing an image (height, width, channels). Expected to be in RGB format with dtype uint8

**Returns**: `Dict[str, Any]` - Dictionary with keys:
  - `mime_type` (str): "image/jpeg"
  - `data` (bytes): JPEG-encoded image data

**Example**:
```python
import numpy as np
from src.utils.media_processing import encode_image_from_array

# Create a test frame (640x480 RGB)
frame = np.zeros((480, 640, 3), dtype=np.uint8)

# Encode to JPEG
blob = encode_image_from_array(frame)
print(blob['mime_type'])  # image/jpeg
print(len(blob['data']))  # Size in bytes
```

#### `get_blank_image(dimensions=None)`

Generate a blank (black) image as a placeholder.

**Description**: Creates a PIL Image filled with zeros (black pixels) with the specified dimensions. Useful as a placeholder when no camera frame is available.

**Parameters**:
- `dimensions` (List[int], optional): List [height, width, channels] for the image. Defaults to [480, 640, 3]

**Returns**: `Image.Image` - PIL Image object containing a black image

**Example**:
```python
from src.utils.media_processing import get_blank_image

# Create blank image with default dimensions
blank = get_blank_image()
print(blank.size)  # (640, 480)

# Create custom size blank image
blank_hd = get_blank_image([1080, 1920, 3])
print(blank_hd.size)  # (1920, 1080)
```

#### `resize_frame(frame, max_size)`

Resize a frame to fit within maximum dimensions while preserving aspect ratio.

**Description**: Uses PIL's thumbnail method to resize the image in-place to fit within the specified maximum width and height, maintaining the original aspect ratio.

**Parameters**:
- `frame` (Image.Image): PIL Image to resize
- `max_size` (Tuple[int, int]): Tuple (max_width, max_height) for the thumbnail

**Returns**: `Image.Image` - The same PIL Image object, resized in-place

**Example**:
```python
from PIL import Image
from src.utils.media_processing import resize_frame

# Load a large image
img = Image.new('RGB', (2048, 1536))
print(img.size)  # (2048, 1536)

# Resize to fit within 1024x1024
resized = resize_frame(img, (1024, 1024))
print(resized.size)  # (1024, 768) - aspect ratio preserved
```

---

## Gemini Client Utilities

### `src.utils.gemini_client`

Functions for initializing and configuring the Gemini Live API client.

#### `get_gemini_client(api_key, http_options)`

Initialize and return a Gemini API client.

**Description**: Creates a Gemini client configured with the provided API key and HTTP options for connecting to the Gemini Live API.

**Parameters**:
- `api_key` (str): Gemini API key for authentication
- `http_options` (Dict[str, Any]): Dictionary containing HTTP configuration options, typically including 'api_version'

**Returns**: `genai.Client` - Configured Gemini client instance

**Raises**:
- `ValueError`: If api_key is None or empty
- `Exception`: If client initialization fails (invalid credentials, etc.)

**Example**:
```python
from src.utils.gemini_client import get_gemini_client

client = get_gemini_client(
    api_key="your-api-key-here",
    http_options={"api_version": "v1alpha"}
)
```

#### `create_speech_config(voice_name)`

Create speech configuration for audio output.

**Description**: Configures the voice settings for Gemini's text-to-speech output, specifying which prebuilt voice to use for synthesized responses.

**Parameters**:
- `voice_name` (str): Name of the prebuilt voice (e.g., "Leda", "Aoede", "Puck", "Charon", "Kore")

**Returns**: `types.SpeechConfig` - SpeechConfig object configured with the specified voice

**Example**:
```python
from src.utils.gemini_client import create_speech_config

# Create speech config with Leda voice
speech_config = create_speech_config("Leda")

# Use with live config (see get_live_config below)
```

#### `get_live_config(system_instruction, response_modalities, speech_config, previous_handle=None)`

Create LiveConnectConfig for Gemini Live API session.

**Description**: Builds the configuration object needed to establish a live streaming connection with Gemini, including system instructions, response settings, context compression, and optional session resumption.

**Parameters**:
- `system_instruction` (str): Text containing the system prompt that defines the agent's personality and behavior
- `response_modalities` (list): List of response types (e.g., ["AUDIO"])
- `speech_config` (types.SpeechConfig): SpeechConfig object with voice settings
- `previous_handle` (str, optional): Session handle for resuming a previous session. If None, starts a new session

**Returns**: `types.LiveConnectConfig` - LiveConnectConfig object ready for establishing a live connection

**Example**:
```python
from src.utils.gemini_client import create_speech_config, get_live_config

# Create speech config
speech_cfg = create_speech_config("Leda")

# Create live config for new session
live_cfg = get_live_config(
    system_instruction="You are a helpful assistant.",
    response_modalities=["AUDIO"],
    speech_config=speech_cfg,
    previous_handle=None
)

# Resume previous session
live_cfg_resume = get_live_config(
    system_instruction="You are a helpful assistant.",
    response_modalities=["AUDIO"],
    speech_config=speech_cfg,
    previous_handle="session-handle-12345"
)
```

---

## Core MediaLoop

### `src.core.media_loop`

Core streaming coordination class and helper functions.

#### `class MediaLoop`

Manages the real-time audio/video streaming loop with Gemini Live API.

**Description**: This class coordinates multiple async tasks:
- `listen_audio`: Captures microphone input and sends to Gemini
- `receive_audio`: Receives audio responses from Gemini
- `play_audio`: Plays received audio through speakers
- `capture_video`: Captures webcam frames and sends to Gemini
- `run`: Orchestrates all tasks in an async task group

**Attributes**:
- `chunk_size` (int): Audio buffer size based on microphone type
- `pya` (pyaudio.PyAudio): PyAudio instance for audio I/O
- `audio_in_queue` (asyncio.Queue): Queue for incoming audio from Gemini
- `session`: Active Gemini Live API session
- `quit` (asyncio.Event): Event to signal shutdown
- `audio_stream_in`: Input audio stream
- `audio_stream_out`: Output audio stream
- `latest_video_frame`: Most recent captured video frame
- `config` (Dict[str, Any]): Configuration dictionary

##### `__init__(config)`

Initialize MediaLoop with configuration.

**Parameters**:
- `config` (Dict[str, Any]): Configuration dictionary containing audio/video settings and API parameters

**Raises**:
- `ValueError`: If MIC_TYPE in config is not supported (must be "dynamic_mic" or "computer_mic")

**Example**:
```python
from src.utils.config_loader import load_config
from src.core.media_loop import MediaLoop

config = load_config()
loop = MediaLoop(config)
```

##### `async listen_audio()`

Capture audio from microphone and stream to Gemini.

**Description**: Opens the default input device and continuously reads audio chunks, sending them to the Gemini Live API session as realtime input. Runs until quit event is set.

**Returns**: None

**Note**: This is an async method meant to be run as a task within the MediaLoop.run() TaskGroup.

##### `async receive_audio()`

Receive audio responses from Gemini and queue for playback.

**Description**: Listens for messages from the Gemini Live API session, handling session resumption updates and queueing audio data for playback. Runs until quit event is set.

**Returns**: None

**Note**: This is an async method meant to be run as a task within the MediaLoop.run() TaskGroup.

##### `async play_audio()`

Play audio responses through speakers.

**Description**: Opens the output audio stream and plays audio chunks received from Gemini. Buffers audio to ensure smooth playback. Runs until quit event is set, then flushes remaining buffer.

**Returns**: None

**Note**: This is an async method meant to be run as a task within the MediaLoop.run() TaskGroup.

##### `async capture_video()`

Capture video frames from webcam and stream to Gemini.

**Description**: Opens the default camera device and captures frames at the configured interval, resizing and encoding them as JPEG before sending to Gemini. Runs until quit event is set.

**Returns**: None

**Note**: This is an async method meant to be run as a task within the MediaLoop.run() TaskGroup.

##### `async run(api_key)`

Run the media loop with all streaming tasks.

**Description**: Establishes connection to Gemini Live API and spawns async tasks for audio input/output and video capture. Coordinates all tasks until shutdown is requested.

**Parameters**:
- `api_key` (str): Gemini API key for authentication

**Returns**: None

**Example**:
```python
import asyncio
from src.utils.config_loader import load_config
from src.core.media_loop import MediaLoop

async def main():
    config = load_config()
    loop = MediaLoop(config)
    await loop.run(api_key="your-api-key")

# Run in thread (as done by session manager)
asyncio.run(main())
```

##### `shutdown()`

Signal all async tasks to stop.

**Description**: Sets the quit event, causing all streaming tasks to exit their loops and clean up resources.

**Returns**: None

**Example**:
```python
# Shutdown is typically called by session manager
loop.shutdown()
```

#### `get_previous_handle()`

Get the session resumption handle from the last session.

**Returns**: `Optional[str]` - Previous session handle or None if no previous session

**Example**:
```python
from src.core.media_loop import get_previous_handle

handle = get_previous_handle()
if handle:
    print(f"Can resume session: {handle}")
```

---

## Session Manager

### `src.core.session_manager`

Thread-safe session lifecycle management.

#### `start_media_session()`

Initialize and start a new MediaLoop session.

**Description**: Creates a new MediaLoop instance with loaded configuration and starts it in a background thread. If a session is already active, this is a no-op.

**Returns**: `str` - Status message: "Started" if new session created, "Already running" if session already active

**Raises**:
- `EnvironmentError`: If GEMINI_API_KEY is not set in environment

**Example**:
```python
from dotenv import load_dotenv
from src.core.session_manager import start_media_session

load_dotenv()
status = start_media_session()
print(status)  # "Started" or "Already running"
```

#### `stop_media_session()`

Shutdown the active MediaLoop session.

**Description**: Signals the MediaLoop to stop all streaming tasks and cleans up resources. If no session is active, this is a no-op.

**Returns**: `str` - Status message: "Stopped" if session was stopped, "Not running" if no session was active

**Example**:
```python
from src.core.session_manager import stop_media_session

status = stop_media_session()
print(status)  # "Stopped" or "Not running"
```

#### `get_session_status()`

Check if a MediaLoop session is currently active.

**Returns**: `str` - Status string: "Running" if session active, "Stopped" if no session active

**Example**:
```python
from src.core.session_manager import get_session_status

status = get_session_status()
if status == "Running":
    print("Session is active")
else:
    print("No active session")
```

**Complete Usage Example**:
```python
from dotenv import load_dotenv
from src.core.session_manager import (
    start_media_session,
    stop_media_session,
    get_session_status
)

# Setup
load_dotenv()

# Check initial status
print(get_session_status())  # "Stopped"

# Start session
result = start_media_session()
print(result)  # "Started"
print(get_session_status())  # "Running"

# Try starting again
result = start_media_session()
print(result)  # "Already running"

# Stop session
result = stop_media_session()
print(result)  # "Stopped"
print(get_session_status())  # "Stopped"
```

---

## UI Interface

### `src.ui.gradio_interface`

Gradio web interface for session control.

#### `create_ui()`

Create and return the Gradio web interface.

**Description**: Builds a Gradio Blocks interface with controls for starting/stopping the media session and displaying the live video feed from the webcam.

**Returns**: `gr.Blocks` - Configured Gradio interface ready to launch

**Example**:
```python
from src.ui.gradio_interface import create_ui

# Create the UI
demo = create_ui()

# Launch locally
demo.launch(share=False)

# Launch with public link
demo.launch(share=True)

# Launch on custom port
demo.launch(server_port=8080)
```

**UI Components**:
- **Start button**: Calls `start_media_session()` and displays result in status textbox
- **Stop button**: Calls `stop_media_session()` and displays result in status textbox
- **Status textbox**: Shows session state ("Started", "Stopped", "Already running", etc.)
- **Video feed**: Live webcam stream using Gradio's Video component with streaming enabled

---

## Type Hints and Constants

### Supported Microphone Types

The application supports two microphone types, configured via `MIC_TYPE` in config.yaml:

- `"dynamic_mic"`: Uses 512-byte audio chunks (lower latency)
- `"computer_mic"`: Uses 1024-byte audio chunks (more stable)

### Common Configuration Keys

**config.yaml**:
- `MIC_TYPE`: "dynamic_mic" or "computer_mic"
- `GEMINI_MODEL`: Model name (e.g., "gemini-2.0-flash-live-001")
- `VOICE_NAME`: Voice for speech synthesis ("Leda", "Aoede", "Puck", "Charon", "Kore")
- `VIDEO_CAPTURE_INTERVAL`: Seconds between video frames (e.g., 0.5)
- `WEB_UI_TITLE`: Title for Gradio interface
- `GEMINI_HTTP_OPTIONS`: HTTP config dict (e.g., {"api_version": "v1alpha"})
- `GEMINI_RESPONSE_MODALITIES`: List of response types (e.g., ["AUDIO"])
- `INSTRUCTIONS_FILE`: Path to system instruction file

**media.yaml**:
- `INPUT_SAMPLE_RATE`: Audio input sample rate in Hz (e.g., 16000)
- `OUTPUT_SAMPLE_RATE`: Audio output sample rate in Hz (e.g., 24000)
- `AUDIO_FORMAT`: PyAudio format constant (e.g., 8 for paInt16)
- `AUDIO_CHANNELS`: Number of audio channels (1 for mono)
- `THUMBNAIL_MAX_SIZE`: Max frame dimensions as [width, height] (e.g., [1024, 1024])
- `BLANK_IMAGE_DIMS`: Placeholder image shape as [height, width, channels]

### Session Status Values

The session manager returns these status strings:
- `"Started"`: New session created successfully
- `"Stopped"`: Session stopped successfully
- `"Running"`: Session is currently active
- `"Not running"`: No session active
- `"Already running"`: Attempted to start when session already active

---

## Error Handling

### Common Exceptions

**FileNotFoundError**:
- Raised by `load_config()` when config files are missing
- Raised by `load_system_instruction()` when instruction file is missing or empty

**ValueError**:
- Raised by `MediaLoop.__init__()` when MIC_TYPE is invalid
- Raised by `get_gemini_client()` when API key is None or empty

**EnvironmentError**:
- Raised by `start_media_session()` when GEMINI_API_KEY environment variable is not set

**KeyError**:
- Raised by `load_system_instruction()` when INSTRUCTIONS_FILE is not in config

**yaml.YAMLError**:
- Raised by `load_config()` when YAML files contain syntax errors

### Error Handling Best Practices

```python
from src.utils.config_loader import load_config, load_system_instruction
from src.core.session_manager import start_media_session

try:
    # Load configuration
    config = load_config()
    instructions = load_system_instruction(config)

    # Start session
    status = start_media_session()
    print(f"Session status: {status}")

except FileNotFoundError as e:
    print(f"Configuration file missing: {e}")
except EnvironmentError as e:
    print(f"Environment setup error: {e}")
except ValueError as e:
    print(f"Configuration value error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Advanced Usage

### Custom Configuration Paths

```python
from src.utils.config_loader import load_config, load_system_instruction
from src.core.media_loop import MediaLoop

# Load from custom paths
config = load_config(
    config_path="custom/my_config.yaml",
    media_path="custom/my_media.yaml"
)

# Update instruction file path
config["INSTRUCTIONS_FILE"] = "custom/my_instructions.txt"

# Load custom instructions
instructions = load_system_instruction(config)

# Create MediaLoop with custom config
loop = MediaLoop(config)
```

### Session Resumption

```python
from src.core.media_loop import get_previous_handle
from src.utils.gemini_client import create_speech_config, get_live_config

# Get handle from previous session
previous_handle = get_previous_handle()

if previous_handle:
    print(f"Resuming session: {previous_handle}")

    # Create live config with resumption
    speech_cfg = create_speech_config("Leda")
    live_cfg = get_live_config(
        system_instruction="You are a helpful assistant.",
        response_modalities=["AUDIO"],
        speech_config=speech_cfg,
        previous_handle=previous_handle
    )
```

### Programmatic UI Launch

```python
from src.ui.gradio_interface import create_ui

# Create UI
demo = create_ui()

# Launch with custom settings
demo.launch(
    server_port=8080,           # Custom port
    share=True,                 # Create public link
    debug=True,                 # Enable debug mode
    server_name="0.0.0.0",      # Allow external connections
    auth=("user", "password"),  # Add authentication
    ssl_verify=False            # Disable SSL verification
)
```

---

## Complete Example

Here's a complete example showing the typical workflow:

```python
import os
from dotenv import load_dotenv

from src.utils.config_loader import load_config, load_system_instruction
from src.utils.gemini_client import get_gemini_client, create_speech_config, get_live_config
from src.core.session_manager import start_media_session, stop_media_session, get_session_status
from src.ui.gradio_interface import create_ui

def main():
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set")

    # 2. Load configuration
    config = load_config()
    print(f"Loaded config with {len(config)} settings")

    # 3. Load system instructions
    instructions = load_system_instruction(config)
    print(f"Loaded {len(instructions)} characters of instructions")

    # 4. Verify Gemini client setup
    client = get_gemini_client(api_key, config["GEMINI_HTTP_OPTIONS"])
    print("Gemini client initialized")

    # 5. Check session status
    status = get_session_status()
    print(f"Initial session status: {status}")

    # 6. Create and launch UI
    demo = create_ui()
    print("Launching Gradio UI...")
    demo.launch(
        server_port=7860,
        share=False,
        debug=False
    )

if __name__ == "__main__":
    main()
```

---

## See Also

- [Architecture Documentation](architecture.md) - System design and data flow
- [README.md](../README.md) - Project overview and getting started guide
- [replication.md](../replication.md) - Step-by-step setup and troubleshooting
