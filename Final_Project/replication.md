## Replication

First, clone the repository so that all source code and assets are available on your local machine. This ensures you have the exact version of the demo we used:

```bash
git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
cd ECE-471-Generative-Machine-Learning/Final_Project
```

### Setup

Before running the demo, we prepare an isolated environment and configure your API credentials.

1. **Virtual Environment (`.venv`)**
   Keeps this project's Python packages separate from your global installation, avoiding version conflicts.

2. **Dependencies (`requirements.txt`)**  
   Specifies exactly which library versions the demo needs (e.g. `gradio`, `pyaudio`, `PyYAML`, Google Gemini).

3. **Credentials File (`.env`)**  
   Stores sensitive keys (Twilio and Gemini) in a `.env` file that is loaded at runtime but not committed to Git.

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

### Running the Demo

Start the application:

```bash
python -m src.app
```

In your browser, navigate to:

```
http://127.0.0.1:7860/
```

Click **Start** to begin the live audio/video session, and **Stop** to end it.

### Troubleshooting

- **Camera issues** – ensure no other application is using the webcam.  
- **Microphone errors** – verify your `MIC_TYPE` in `config.yaml` matches your hardware.  
- **API errors** – confirm keys in `.env` are correct and valid.  
```
