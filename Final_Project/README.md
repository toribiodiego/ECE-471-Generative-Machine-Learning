> This directory contains the final project for **Generative Machine Learning (ECE-471)**, an Interactive Multimodal (Audio-Video) Agent that captures live audio and video via the Gemini Live API for real-time speech synthesis.

## Interactive Multimodal Agent (Audio-Video)

Everything required to run *Agnes*—source, configs, tests, and exhibition assets—lives in this folder. The project uses a modular architecture with dedicated modules for media processing, session management, and UI components. Core pieces include the async streaming loop, YAML configs, a Gradio web interface, the insult-packed system prompt, and exhibition artifacts.

### Objective
Build an always-on demo that streams webcam frames and mic audio to Gemini 2.0, plays back the model's synthesized speech, and lets visitors banter with a sarcastic "AI face." The project highlights low-latency media pipelines, prompt-driven personality control, and a lightweight Gradio front-end—all on commodity hardware.

### Exhibition

<p align="center">
  <img src="artifacts/03-exhibition.jpeg" alt="Agnes at the GenML exhibition" width="60%">
</p>

<p align="center"><strong>Figure 1</strong>: <em>Agnes</em> at the GenML exhibition.</p>

### Approach

Webcam video and audio stream into Gemini's Live API<sup>[1](#ref1)</sup>; Gemini returns speech that we play back in real time. Gradio wraps the loop in a one-click web UI, while configs toggle mic type, model, and voice. On startup we load the system instructions, so *Agnes* begins roasting whoever steps into view.

The refactored codebase organizes functionality into clean modules: utilities handle config and media processing, core modules manage the streaming loop and sessions, and the UI layer presents a simple web interface. Everything's tested with a comprehensive suite (93 tests, 99% coverage) to keep the chaos under control.

<p align="center">
  <img src="artifacts/02-flowchart.png" alt="System flowchart showing data flow" width="70%">
</p>

<p align="center"><strong>Figure 2</strong>: System architecture showing the audio-video streaming loop through Gemini Live API.</p>


### Directory Structure

```
.
├── src/                    # Source code (modular architecture)
│   ├── app.py             # Main entry point
│   ├── config/            # Configuration files
│   │   ├── config.yaml    # Dev-level knobs (mic, model, voice)
│   │   ├── media.yaml     # Runtime A/V parameters
│   │   └── instructions.txt  # System prompt
│   ├── core/              # Core application logic
│   │   ├── media_loop.py  # Async streaming loop
│   │   └── session_manager.py  # Session lifecycle
│   ├── ui/                # User interface
│   │   └── gradio_interface.py  # Web UI components
│   └── utils/             # Utility modules
│       ├── config_loader.py     # Config management
│       ├── gemini_client.py     # Gemini API client
│       └── media_processing.py  # Image/audio processing
├── tests/                 # Test suite (93 tests, 99% coverage)
├── output/                # Runtime outputs (logs, recordings, artifacts)
├── artifacts/             # Exhibition materials (poster, photos, flowchart)
├── replication.md         # Step-by-step setup guide
├── requirements.txt       # Pinned dependencies
└── setup.sh              # Environment bootstrapper
```

**Quick tour:**
- `src/app.py` — launch the application from here
- `src/config/` — tweak mic settings, model choice, personality
- `src/core/` — the heart of the streaming loop and session management
- `src/ui/` — Gradio web interface components
- `src/utils/` — helpers for config, media, and API client setup
- `tests/` — comprehensive test suite covering all modules

### Getting Started

**1. Clone and navigate:**
```bash
git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
cd ECE-471-Generative-Machine-Learning/Final_Project
```

**2. Set up environment:**
```bash
chmod +x setup.sh
source ./setup.sh
```

This creates a `.venv/` virtual environment, installs all dependencies from `requirements.txt`, and generates a `.env` template for your API keys.

**3. Add credentials:**

Open `.env` and fill in your API keys:
```ini
GEMINI_API_KEY=your_gemini_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

**4. Launch the app:**
```bash
python -m src.app
```

Head to `http://127.0.0.1:7860/` in your browser, click **Start** to begin the live session, and **Stop** to end it.

### Project Highlights

- **Modular architecture** — clean separation between config, core logic, UI, and utilities
- **Comprehensive testing** — 93 tests with 99% code coverage
- **Real-time multimodal streaming** — sub-second latency for audio and video
- **Personality control** — system prompt drives conversational behavior
- **Production-ready** — async design, error handling, session management

### Results

A fully functioning multimodal agent that insults users in real time with negligible latency.

### On Replication

For a detailed step-by-step local setup guide (environment creation, credentials, troubleshooting), see **[replication.md](replication.md)**.


### References

<a name="ref1" href="https://ai.google.dev/gemini-api/docs/live">[1]</a>: Google Gemini Live API documentation – official guide to streaming audio/video into Gemini models.
