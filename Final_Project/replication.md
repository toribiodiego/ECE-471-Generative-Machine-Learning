## Replication Guide

This guide walks you through setting up and running *Agnes* on your local machine. You'll clone the repo, configure your environment, set up API credentials, and launch the interactive multimodal agent.

---

## Step 1: Clone the Repository

First, grab the source code and navigate to the project directory:

```bash
git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
cd ECE-471-Generative-Machine-Learning/Final_Project
```

This gets you the complete refactored codebase with the modular `src/` structure, tests, configs, and exhibition materials.

---

## Step 2: Set Up Your Environment

The project uses a virtual environment to keep dependencies isolated from your system Python installation.

**Run the automated setup script:**

```bash
chmod +x setup.sh
source ./setup.sh
```

This script will:
- Create a `.venv/` virtual environment (hidden directory)
- Install all dependencies from `requirements.txt` (Gradio, PyAudio, Google Gemini SDK, etc.)
- Generate a `.env` template file for your API credentials

You should see output confirming the virtual environment was created and packages were installed.

---

## Step 3: Configure API Credentials

Open the newly created `.env` file in your editor and fill in your API key:

```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

**Where to get this:**
- **Gemini API Key**: Get one from [Google AI Studio](https://ai.google.dev/gemini-api/docs)

Save the file. The application will load these credentials at runtime using `python-dotenv`.

---

## Step 4: Launch the Application

With your environment configured, start the Gradio web interface:

```bash
python -m src.app
```

You should see output indicating the Gradio server is running:

```
Running on local URL:  http://127.0.0.1:7860
```

**Optional flags:**
- `--port 8080` — run on a different port
- `--share` — create a public shareable link
- `--debug` — enable verbose logging

---

## Step 5: Test the Interaction

1. **Open your browser** and navigate to `http://127.0.0.1:7860/`

2. **Start a session:**
   - Click the **Start** button in the web interface
   - Grant camera and microphone permissions when prompted
   - You should see your webcam feed appear and the status change to "Running"

3. **Interact with Agnes:**
   - Step in front of the camera
   - Say something—*Agnes* will respond with synthesized speech through your speakers
   - The agent uses the personality defined in `src/config/instructions.txt` (by default, sarcastic roasting mode)

4. **Stop the session:**
   - Click the **Stop** button to end the streaming session
   - The video feed will stop and the status will show "Stopped"

**What you should observe:**
- Near real-time response (sub-second latency)
- Audio playback through your system speakers
- Live video feed showing what the agent sees
- Personality-driven responses based on the system prompt

---

## Troubleshooting

### Camera Issues
- **Symptom**: Camera feed doesn't start or shows black screen
- **Fix**: Ensure no other application is using the webcam (close Zoom, Teams, etc.)
- **Check**: Browser permissions are granted for camera access

### Microphone Errors
- **Symptom**: Audio not being captured or playback fails
- **Fix**: Verify your `MIC_TYPE` in `src/config/config.yaml` matches your hardware
- **Options**: `"computer_mic"` (default) or `"dynamic_mic"`
- **Check**: System audio permissions are enabled

### API Errors
- **Symptom**: Error messages about authentication or rate limits
- **Fix**: Confirm your API keys in `.env` are correct and valid
- **Check**: Gemini API key has appropriate permissions and isn't expired
- **Quota**: Verify you haven't exceeded Gemini API rate limits

### Module Import Errors
- **Symptom**: `ModuleNotFoundError` or import errors
- **Fix**: Make sure you activated the virtual environment: `source .venv/bin/activate`
- **Check**: All dependencies are installed: `.venv/bin/pip list`

### Port Already in Use
- **Symptom**: Error message about port 7860 being occupied
- **Fix**: Use a different port: `python -m src.app --port 8080`
- **Alternative**: Find and kill the process using port 7860

---

## Configuration Tips

### Customize Personality

Edit `src/config/instructions.txt` to change *Agnes*'s behavior:
- Make it polite and helpful
- Add domain-specific knowledge
- Adjust tone and style

### Adjust Model Settings

Modify `src/config/config.yaml` to tweak:
- `GEMINI_MODEL`: Switch between Gemini models
- `VOICE_NAME`: Change the voice (options: Leda, Puck, Charon, Kore)
- `VIDEO_CAPTURE_INTERVAL`: Adjust frame rate (lower = less bandwidth)

### Media Parameters

Update `src/config/media.yaml` for audio/video settings:
- Sample rates (input/output)
- Audio format and channels
- Thumbnail size limits

---

## Next Steps

Once you have *Agnes* running:
- Try different system prompts to experiment with personalities
- Adjust model parameters to optimize latency vs. quality
- Check out the test suite: `pytest tests/ -v`
- Explore the modular codebase in `src/` to understand the architecture

**For questions or issues:**
- Check **[docs/troubleshooting.md](docs/troubleshooting.md)** for solutions to common problems with audio, video, network, and performance issues
- Refer to the main **[README.md](README.md)** for project structure and highlights
