> This directory contains the final project for **Generative Machine Learning (ECE-471)**, an Interactive Multimodal (Audio-Video) Agent that captures live audio and video via the Gemini Live API for real-time speech synthesis.

## Interactive Multimodal Agent (Audio-Video)

This document guides you through setting up and running the Generative Machine Learning live audio/video demo, and provides a high-level overview of its architecture and prompt engineering.


### Exhibition

![photo from GenML live-demo](artifacts/exhibition.jpeg)

**Figure 1**: Photo from the GenML exhibition showing *Agnes*, the interactive multimodal agent, in action.


### Approach

We pair Google Gemini 2.0’s backend with a lightweight Gradio front-end: every webcam frame and microphone chunk is streamed to Gemini and the model returns synthesized speech in real time.  The only hardware requirements are a working camera and either a dynamic or built-in computer mic; configuration lives in `config.yaml`, while implementation specifics are in `app.py`.  At launch we seed Gemini with custom system instructions so the agent—Agnes—immediately begins roasting whoever appears on-screen.

### On Replication

A full step-by-step guide for running Agnes locally—including environment setup, credentials, and troubleshooting—is in **[replication.md](replication.md)**.

### Directory Structure

```
.
├── README.md
├── replication.md
├── app.py
├── artifacts
│   ├── agnes_poster.pdf
│   └── exhibition.jpeg
├── config.yaml
├── instructions.txt
├── media.yaml
├── requirements.txt
└── setup.sh
```

- **`app.py`**   main application entry-point  
- **`config.yaml`**   development-friendly overrides (mic type, model, instructions file, voice)  
- **`media.yaml`**   detailed runtime parameters (sample rates, video intervals, etc.)  
- **`instructions.txt`**   system prompt defining agent behaviour  
- **`requirements.txt`**   pinned Python dependencies  
- **`setup.sh`**   helper script to scaffold your environment  


### Results


<br>
