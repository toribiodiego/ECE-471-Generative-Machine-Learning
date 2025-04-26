> This directory contains the final project for **Generative Machine Learning (ECE‑471)**, an Interactive Multimodal (Audio‑Video) Agent that captures live audio and video via the Gemini Live API for real‑time speech synthesis.

## Interactive Multimodal Agent (Audio-Video)

This document guides you through setting up and running the Generative Machine Learning live audio/video demo, and provides a high-level overview of its architecture and prompt engineering.


### Exhibition

![photo from GenML live-demo](artifacts/exhibition.jpeg)

**Figure 1**: photo of Agnes, the interactive multimodal agent in the GenML exhibition.


### Approach

- **MediaLoop**  
  - Captures real-time audio (via `pyaudio`) and video frames (via `OpenCV`).  
  - Sends encoded media to Gemini and receives synthesized audio for playback.  
  - Streams live video feed alongside model-generated responses.

- **Gemini Configuration**  
  - Model: specified by `config["GEMINI_MODEL"]` (default: `gemini-2.0-flash-exp`).  
  - HTTP options and response modalities configured in `config["GEMINI_HTTP_OPTIONS"]` and `config["GEMINI_RESPONSE_MODALITIES"]`.
  - System instructions loaded from `instructions.txt` via `load_system_instruction()`.

- **Encoding Helpers**  
  - `encode_text`, `encode_audio`, `encode_image_from_array` convert data to base64 MIME format for transmission.

- **Gradio UI**  
  - Uses `gradio.Blocks` to provide controls (`Start`, `Stop`) and display live video and status.

<br>



#### On Systems Instructions

- The agent’s behavior is driven by **system instructions** in `instructions.txt`.  
- To change how the model interacts, edit **only** `instructions.txt`.  
- To switch models or voices, update **`config.yaml`** (no code changes required).

<br>

#### Tools


<br>


### Directory Structure

```
.
├── README.md
├── app.py
├── artifacts
│   ├── agnes_poster.pdf
│   └── exhibition.jpeg
├── config.yaml
├── instructions.txt
├── media.yaml
├── requirements.txt
└── setup.sh
```

- **`app.py`**: main application entrypoint  
- **`config.yaml`**: development‑friendly overrides (e.g. mic type, model, instructions file, voice)  
- **`media.yaml`**: detailed runtime parameters (e.g. sample rates, video intervals)  
- **`instructions.txt`**: system prompt defining agent behavior  
- **`requirements.txt`**: lists all Python dependencies with pinned versions  
- **`setup.sh`**: helper script to scaffold your environment  


### Replication

First, clone the repository so that all source code and assets are available on your local machine. This ensures you have the exact version of the demo we used:

```bash
git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
cd ECE-471-Generative-Machine-Learning/Final_Project
```



<br>


#### Setup

Before running the demo, we prepare an isolated environment and configure your API credentials:

1. **Virtual Environment (`venv`)**  
   - Keeps this project’s Python packages separate from your global installation, avoiding version conflicts.

2. **Dependencies (`requirements.txt`)**  
   - Specifies exactly which library versions the demo needs (e.g., `gradio`, `pyaudio`, `PyYAML`, Google Gemini).

3. **Credentials File (`.env`)**  
   - Stores sensitive keys (Twilio and Gemini) in a `.env` file that is loaded at runtime but not committed to Git.

4. **Automated Setup Script**  
   Run the provided script to do all of the above in one step:
   ```bash
   chmod +x setup.sh
   source ./setup.sh
   ```
   Afterwards, open the newly created `.env` and fill in:
   ```ini
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   GEMINI_API_KEY=your_gemini_api_key
   ```


<br>


#### Running the Demo

Start the application:
```bash
python app.py
```

In your browser, navigate to:
```
http://127.0.0.1:7860/
```
Click **Start** to begin the live audio/video session, and **Stop** to end it.

<br>



#### Troubleshooting

- **Camera issues**: ensure no other application is using the webcam.  
- **Microphone errors**: verify your `MIC_TYPE` in `config.yaml` matches your hardware.  
- **API errors**: confirm keys in `.env` are correct and valid.  