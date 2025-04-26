> This directory contains the final project for **Generative Machine Learning (ECE-471)**, an Interactive Multimodal (Audio-Video) Agent that captures live audio and video via the Gemini Live API for real-time speech synthesis.

## Interactive Multimodal Agent (Audio-Video)

All source code, configuration files, and assets needed to run *Agnes*—our live, webcam-driven multimodal troll—are collected here. You’ll find the Python application (`app.py`), YAML configs for audio/video and model settings, Gradio UI scaffolding, the insult-laden system prompt, and exhibition artifacts such as screenshots and posters.

### Objective  
Create an always-on demonstrator that streams real-time video frames and microphone audio to Gemini 2.0, then plays back the model’s synthesized speech so visitors can banter with a sarcastic “AI face.” The project explores low-latency media pipelines, prompt engineering for personality control, and lightweight front-end delivery via Gradio—all while keeping hardware requirements to a commodity webcam and mic.

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

### References

https://ai.google.dev/gemini-api/docs/live

