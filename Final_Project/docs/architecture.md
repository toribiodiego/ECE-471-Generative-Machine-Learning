# Architecture Documentation

This document provides a comprehensive technical overview of the Agnus multimodal agent system, covering system design, data flow, component interactions, and deployment considerations.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [Component Breakdown](#component-breakdown)
- [Data Flow](#data-flow)
- [Async Task Coordination](#async-task-coordination)
- [Configuration Management](#configuration-management)
- [Error Handling and Resilience](#error-handling-and-resilience)
- [Performance Considerations](#performance-considerations)
- [Deployment Guide](#deployment-guide)

---

## System Overview

Agnus is a real-time multimodal conversational agent that combines audio and video streaming with Google's Gemini Live API to create an interactive experience. The system captures webcam frames and microphone audio, sends them to Gemini for processing, and plays back synthesized speech responses with sub-second latency.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Gradio Web UI                          │
│              (User Control Interface)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Session Manager                            │
│         (Thread-safe lifecycle control)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    MediaLoop                                │
│        (Async streaming coordination)                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Audio In   │  │   Video In   │  │  Audio Out   │     │
│  │   (PyAudio)  │  │   (OpenCV)   │  │  (PyAudio)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Gemini Live API    │
                  │  (Audio + Video →    │
                  │   Speech Synthesis)  │
                  └──────────────────────┘
```

### Key Features

- **Real-time multimodal streaming**: Simultaneous audio and video capture with near-instantaneous response
- **Sub-second latency**: Optimized async design keeps total round-trip time under 1 second
- **Personality control**: System prompt drives conversational behavior without code changes
- **Production-ready**: Thread-safe session management, comprehensive error handling, 99% test coverage
- **Modular design**: Clean separation of concerns enables independent testing and maintenance

---

## Architecture Principles

The system follows these core design principles:

### 1. Separation of Concerns

The codebase is organized into distinct layers:

- **Configuration Layer** (`src/config/`): YAML configs and system prompts
- **Utility Layer** (`src/utils/`): Pure functions for config loading, media processing, API client setup
- **Core Layer** (`src/core/`): Business logic for streaming and session management
- **Presentation Layer** (`src/ui/`): Gradio web interface

Each layer has well-defined responsibilities and minimal coupling to other layers.

### 2. Async-First Design

All I/O-bound operations use Python's `asyncio` to maximize concurrency:

- Audio capture runs in parallel with video capture
- Audio playback doesn't block audio input
- Frame encoding happens in background threads
- All tasks coordinate through async primitives (queues, events)

### 3. Fail-Safe Defaults

The system prioritizes reliability:

- Missing config values have sensible defaults
- API errors don't crash the application
- Session shutdown is always graceful
- Resource cleanup happens even on error paths

### 4. Testability

Every module is designed for easy testing:

- Dependency injection for external services (Gemini client, PyAudio)
- Pure functions with no side effects in utilities
- Mocked I/O in tests (no actual camera/mic required)
- 99% code coverage (224/227 statements)

---

## Component Breakdown

### Configuration Layer (`src/config/`)

**Purpose**: Externalize all runtime parameters so behavior changes don't require code modifications.

**Files**:
- `config.yaml`: Development-level settings (model choice, voice, mic type, video capture interval)
- `media.yaml`: Media processing parameters (sample rates, audio format, thumbnail size)
- `instructions.txt`: System prompt that controls agent personality

**Key Functions** (`src/utils/config_loader.py`):
- `load_config()`: Merges config.yaml and media.yaml into single dict
- `load_system_instruction()`: Loads system prompt from instructions.txt
- `get_config_value()`: Safe config access with defaults

### Utility Layer (`src/utils/`)

**Purpose**: Provide reusable, stateless functions for common operations.

#### Media Processing (`media_processing.py`)

Handles image and audio transformations:

- `encode_image_from_array(arr)`: Converts numpy array to JPEG blob for Gemini
- `resize_frame(frame, max_size)`: Creates thumbnails to reduce bandwidth
- `get_blank_image()`: Generates placeholder image when camera unavailable

#### Gemini Client (`gemini_client.py`)

Encapsulates all Gemini API interactions:

- `get_gemini_client(api_key)`: Initializes Gemini client with authentication
- `get_live_config()`: Constructs LiveConnectConfig with system prompt and settings
- `create_speech_config()`: Sets up voice parameters for speech synthesis

Session resumption is supported via `previous_handle` parameter for maintaining conversation context across restarts.

### Core Layer (`src/core/`)

**Purpose**: Implement the business logic for streaming and session lifecycle.

#### MediaLoop (`media_loop.py`)

The heart of the system. Coordinates four concurrent async tasks:

**Task 1: Audio Input** (`listen_audio`)
- Captures mic input via PyAudio
- Chunks audio into 512-byte (dynamic mic) or 1024-byte (computer mic) buffers
- Sends audio to Gemini in real-time via `session.send_realtime_input(audio=...)`

**Task 2: Audio Output** (`play_audio`)
- Pulls audio chunks from async queue
- Plays back through PyAudio output stream
- Maintains smooth playback without blocking input

**Task 3: Video Capture** (`capture_video`)
- Grabs webcam frames via OpenCV at configurable interval (default 0.5s)
- Resizes and encodes frames to JPEG
- Sends to Gemini via `session.send_realtime_input(video=...)`

**Task 4: Message Receiving** (`receive_audio`)
- Listens for audio responses from Gemini
- Pushes received audio to playback queue
- Handles server-sent messages and turn completion events

All tasks run concurrently in an `asyncio.TaskGroup` and coordinate via:
- `audio_in_queue`: Async queue for Gemini → speaker audio
- `quit`: Async event for graceful shutdown signal
- `session`: Shared Gemini Live session object

**Shutdown**: When `quit.is_set()`, all tasks exit their loops. Resources (PyAudio streams, camera, Gemini session) are cleaned up in `shutdown()`.

#### Session Manager (`session_manager.py`)

Provides thread-safe session lifecycle control:

- `start_media_session()`: Creates MediaLoop, spawns background thread running `asyncio.run(loop.run())`
- `stop_media_session()`: Signals quit event and waits for graceful shutdown
- `get_session_status()`: Returns "Running", "Stopped", or error state

Thread safety is ensured via `threading.Lock` protecting global `_media_loop` and `_media_loop_thread` state.

**Error handling**: Missing API keys raise `EnvironmentError` with helpful message directing users to create `.env` file.

### Presentation Layer (`src/ui/`)

#### Gradio Interface (`gradio_interface.py`)

Minimal web UI with three components:

- **Video feed**: Displays live webcam stream showing what Gemini sees
- **Status text**: Shows session state ("Running", "Stopped", error messages)
- **Control buttons**: Start/Stop buttons calling session manager functions

The UI is stateless—all state lives in the session manager. Button clicks trigger session lifecycle functions and update status display.

**Layout**:
```
┌───────────────────────────────────┐
│  Gemini Audio/Video Demo          │
├───────────────────────────────────┤
│  [Video Feed]                     │
│                                   │
│  Status: Running                  │
│                                   │
│  [Start] [Stop]                   │
└───────────────────────────────────┘
```

---

## Data Flow

### Complete Request-Response Cycle

```
1. User speaks → Microphone
                    ↓
2. PyAudio captures 512/1024 byte chunks
                    ↓
3. MediaLoop.listen_audio() → Gemini Live session.send_realtime_input(audio=chunk)
                    ↓
4. Gemini processes audio + recent video frames
                    ↓
5. Gemini generates speech response
                    ↓
6. MediaLoop.receive_audio() ← session (async generator yields audio chunks)
                    ↓
7. Audio chunks → audio_in_queue.put()
                    ↓
8. MediaLoop.play_audio() ← audio_in_queue.get()
                    ↓
9. PyAudio plays chunk → Speakers → User hears response
```

**Parallel video path**:
```
1. Webcam → OpenCV VideoCapture.read()
                    ↓
2. MediaLoop.capture_video() resizes frame (max 1024x1024)
                    ↓
3. Encode to JPEG blob
                    ↓
4. session.send_realtime_input(video=blob) every 0.5s
                    ↓
5. Gemini maintains visual context for responses
```

### Timing Characteristics

- **Audio latency**: ~50-100ms (chunk size / sample rate)
- **Video refresh**: 500ms default (configurable via VIDEO_CAPTURE_INTERVAL)
- **Gemini response time**: 200-800ms (depends on prompt complexity)
- **Total round-trip**: Typically 500-1200ms from user speech to audio playback start

Latency is kept low by:
- Small audio chunk sizes (512/1024 bytes)
- Async I/O preventing blocking
- Streaming responses (audio plays as it arrives, not after full response)

---

## Async Task Coordination

The MediaLoop uses Python 3.11+ `asyncio.TaskGroup` for structured concurrency. All tasks start together and exit together.

### Task Lifecycle

```python
async with asyncio.TaskGroup() as tg:
    # Spawn all tasks
    tg.create_task(self.listen_audio())
    tg.create_task(self.receive_audio())
    tg.create_task(self.play_audio())
    tg.create_task(self.capture_video())

    # Block until quit event is set
    await self.quit.wait()

    # TaskGroup ensures all tasks are cancelled/completed before exiting
```

### Coordination Primitives

**1. Async Queue** (`audio_in_queue`)
- Producer: `receive_audio()` puts audio chunks from Gemini
- Consumer: `play_audio()` gets chunks and plays them
- Backpressure: Queue has max size to prevent memory buildup if playback falls behind

**2. Async Event** (`quit`)
- Set by `shutdown()` when user clicks Stop button
- All tasks check `while not self.quit.is_set()` in their loops
- Provides clean exit without exception-based cancellation

**3. Shared State** (`session`, `latest_video_frame`)
- `session`: Gemini Live session shared across tasks for send/receive
- `latest_video_frame`: Most recent frame (could be displayed in UI or logged)
- No locking needed—async tasks run in single thread, event loop handles scheduling

### Error Propagation

If any task raises an exception:
1. `TaskGroup` cancels all other tasks
2. Exception propagates to `run()` caller
3. Session manager catches exception, logs it, marks session as failed
4. UI shows error status to user

This fail-fast approach ensures partial failures don't leave the system in inconsistent state.

---

## Configuration Management

### Configuration Files

**config.yaml** (development settings):
```yaml
MIC_TYPE: dynamic_mic          # or computer_mic
GEMINI_MODEL: gemini-2.0-flash-live-001
VOICE_NAME: Leda               # Leda, Puck, Charon, Kore
VIDEO_CAPTURE_INTERVAL: 0.5    # seconds between frames
WEB_UI_TITLE: Gemini Audio/Video Demo
```

**media.yaml** (media processing):
```yaml
INPUT_SAMPLE_RATE: 16000       # Hz, must match Gemini requirements
OUTPUT_SAMPLE_RATE: 24000      # Hz, Gemini speech output rate
AUDIO_FORMAT: 8                # pyaudio.paInt16
AUDIO_CHANNELS: 1              # mono
THUMBNAIL_MAX_SIZE: [1024, 1024]  # max frame dimensions
BLANK_IMAGE_DIMS: [480, 640, 3]   # placeholder image shape
```

### Environment Variables

Sensitive credentials live in `.env` (never committed):
```ini
GEMINI_API_KEY=your_api_key_here
```

Loading via `python-dotenv` in `session_manager.py:start_media_session()`.

### Merging Strategy

`load_config()` merges both YAML files into a single dictionary:
1. Load `config.yaml` → dict A
2. Load `media.yaml` → dict B
3. Return `{**A, **B}` (media.yaml values override config.yaml if keys conflict)

This allows logical separation (dev settings vs. media params) while providing a single config interface to application code.

---

## Error Handling and Resilience

### API Key Validation

Missing `GEMINI_API_KEY` raises `EnvironmentError` with actionable message:
```
GEMINI_API_KEY not found in environment. Please create a .env file with your API key.
```

Caught by Gradio UI, displayed to user as status message.

### Camera/Mic Failures

If camera can't open:
- `capture_video()` prints warning and exits gracefully
- Other tasks continue running (audio-only mode)

If mic fails:
- `listen_audio()` catches exception, logs error
- TaskGroup propagates exception → session stops with error status

### Network Errors

Gemini session failures:
- Connection errors during `client.aio.live.connect()` propagate to session manager
- User sees "Failed to start session" with error details
- Retry requires manual Stop → Start

### Resource Cleanup

`shutdown()` ensures cleanup even on errors:
```python
def shutdown(self):
    self.quit.set()  # Signal all tasks to exit

    if self.audio_stream_in:
        self.audio_stream_in.stop_stream()
        self.audio_stream_in.close()

    if self.audio_stream_out:
        self.audio_stream_out.stop_stream()
        self.audio_stream_out.close()

    if self.pya:
        self.pya.terminate()
```

Called by session manager after MediaLoop thread exits, whether via normal shutdown or exception.

---

## Performance Considerations

### Latency Optimization

**Audio chunk size**: Smaller chunks reduce latency but increase CPU overhead. Current values (512/1024 bytes) balance responsiveness with efficiency.

**Video frame rate**: Sending frames every 500ms provides sufficient visual context without saturating bandwidth. Adjust `VIDEO_CAPTURE_INTERVAL` for different tradeoffs.

**Frame compression**: JPEG encoding with quality 85 keeps frame size under 50KB while maintaining clarity.

### Memory Management

**Audio queue bounds**: Queue max size prevents unbounded growth if playback can't keep up with incoming audio.

**Frame resizing**: Thumbnailing to max 1024x1024 keeps per-frame memory under 3MB (1024 × 1024 × 3 bytes RGB).

**No recording**: Audio/video aren't saved to disk by default, avoiding I/O overhead. Enable logging to `output/` if needed.

### CPU Utilization

Async I/O keeps CPU free for Gemini processing:
- Audio I/O delegated to PyAudio C library
- Frame capture uses OpenCV's optimized routines
- JPEG encoding happens in `asyncio.to_thread()` background threads

Typical CPU usage: 10-20% on modern hardware (4+ cores).

### Network Bandwidth

Upload bandwidth:
- Audio: ~16KB/s (16kHz × 1 byte/sample)
- Video: ~100KB/s (50KB/frame × 2 frames/sec)
- Total: ~120KB/s (~1 Mbps)

Download bandwidth:
- Speech audio: ~24KB/s (24kHz × 1 byte/sample)

Requires stable broadband connection (5+ Mbps recommended).

---

## Deployment Guide

### Local Development

1. **Clone and navigate**:
   ```bash
   git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
   cd ECE-471-Generative-Machine-Learning/Final_Project
   ```

2. **Set up environment**:
   ```bash
   chmod +x setup.sh
   source ./setup.sh
   ```

3. **Add credentials**:
   Create `.env`:
   ```ini
   GEMINI_API_KEY=your_key_here
   ```

4. **Run application**:
   ```bash
   python -m src.app
   ```
   Open `http://127.0.0.1:7860/`

### Production Deployment

**System Requirements**:
- Python 3.11+
- Webcam (any USB/built-in camera supported by OpenCV)
- Microphone (USB or 3.5mm jack)
- 4+ CPU cores
- 4GB+ RAM
- 5+ Mbps internet connection

**Deployment Options**:

**Option 1: Local Server**
```bash
python -m src.app --port 8080 --share
```
The `--share` flag creates a public Gradio link (tunneled through Gradio's servers).

**Option 2: Docker** (not yet implemented)
Future work: Create Dockerfile with PyAudio, OpenCV, and Python dependencies.

**Option 3: Cloud VM**
Deploy on AWS EC2, GCP Compute Engine, or Azure VM:
- Use t3.medium or equivalent (2 vCPUs, 4GB RAM)
- Open port 7860 in security group
- Run as systemd service for auto-restart

**Security Considerations**:
- Never commit `.env` file
- Use firewall to restrict access to Gradio port
- Consider adding authentication to Gradio interface (`gr.Interface(..., auth=...)`)
- Rotate API keys regularly

### Monitoring

**Logs**: Application prints to stdout. Redirect to file:
```bash
python -m src.app > output/logs/app.log 2>&1
```

**Health checks**: Hit Gradio health endpoint:
```bash
curl http://localhost:7860/api/health
```

**Metrics to track**:
- Session start/stop events
- Audio queue depth (detect playback lag)
- Frame capture rate (detect camera issues)
- Gemini API errors (detect quota/network issues)

### Troubleshooting

**Camera not detected**:
- Check `ls /dev/video*` on Linux
- Verify camera permissions (macOS: System Preferences → Security → Camera)
- Test with `python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`

**Microphone not working**:
- List devices: `python -m pyaudio` (shows all available audio devices)
- Update `MIC_TYPE` in `config.yaml` (try both `computer_mic` and `dynamic_mic`)
- Check system audio input level isn't muted

**High latency**:
- Reduce `VIDEO_CAPTURE_INTERVAL` (less frequent frames = faster audio processing)
- Check network latency: `ping google.com`
- Verify CPU isn't saturated: `top` or `htop`

**Gemini API rate limits**:
- Check quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
- Reduce frame rate if hitting bandwidth limits
- Implement exponential backoff for retries (future work)

---

## Future Enhancements

Potential improvements for production deployment:

1. **Session persistence**: Save conversation history to disk, reload on restart
2. **Multi-user support**: Session manager currently handles one global session; extend to per-user sessions
3. **Audio recording**: Save input/output audio to `output/recordings/` for debugging
4. **Metrics dashboard**: Expose Prometheus metrics (session count, latency, error rate)
5. **Dynamic frame rate**: Adjust `VIDEO_CAPTURE_INTERVAL` based on network conditions
6. **Graceful degradation**: Fall back to audio-only if camera fails
7. **WebRTC integration**: Replace Gradio with WebRTC for lower-latency browser streaming

---

## References

- [Gemini Live API Documentation](https://ai.google.dev/gemini-api/docs/live)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [OpenCV Python Tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [Gradio Documentation](https://www.gradio.app/docs)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
