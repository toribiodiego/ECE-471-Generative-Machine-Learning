[Documentation Index](README.md) > Deployment

# Deployment Guide

This guide provides comprehensive instructions for deploying the Agnus multimodal agent in production environments, covering hardware requirements, environment configuration, deployment options, and performance optimization.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Hardware Requirements](#hardware-requirements)
- [Environment Configuration](#environment-configuration)
- [Local Development Deployment](#local-development-deployment)
- [Production Deployment Options](#production-deployment-options)
- [Performance Optimization](#performance-optimization)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Common Deployment Issues](#common-deployment-issues)

---

## Prerequisites

Before deploying Agnus, ensure you have:

1. **Python 3.11+**: Required for async TaskGroup support
   ```bash
   python3 --version  # Should show 3.11 or higher
   ```

2. **Git**: For cloning the repository
   ```bash
   git --version
   ```

3. **Gemini API Key**: Obtain from [Google AI Studio](https://ai.google.dev/gemini-api/docs)

4. **Camera and Microphone**: USB or built-in devices supported by OpenCV and PyAudio

5. **Network Connection**: Stable broadband (5+ Mbps recommended)

---

## Hardware Requirements

### Minimum Requirements

For basic functionality:

- **CPU**: 2 cores, 2.0 GHz or higher
- **RAM**: 2 GB available
- **Storage**: 500 MB for application and dependencies
- **Camera**: Any USB webcam or built-in camera (minimum 480p)
- **Microphone**: 3.5mm jack or USB microphone
- **Network**: 3 Mbps upload, 2 Mbps download

### Recommended Requirements

For optimal performance:

- **CPU**: 4+ cores, 2.5 GHz or higher
- **RAM**: 4 GB available
- **Storage**: 2 GB for application, logs, and recordings
- **Camera**: 720p or 1080p USB webcam with good low-light performance
- **Microphone**: USB condenser microphone or dynamic mic with audio interface
- **Network**: 10+ Mbps upload, 5+ Mbps download with low latency (<50ms)

### Camera Compatibility

**Supported**:
- Built-in laptop webcams
- USB webcams (Logitech, Microsoft, etc.)
- Any camera recognized by OpenCV (v4l2 on Linux, AVFoundation on macOS)

**Verification**:
```bash
# Test camera access
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAILED')"
```

**Common Issues**:
- **macOS**: Grant camera permissions in System Preferences → Security & Privacy → Camera
- **Linux**: Ensure user is in `video` group: `sudo usermod -a -G video $USER`
- **Windows**: Check Device Manager for camera driver issues

### Microphone Compatibility

**Supported Types**:
- **Computer Mic** (built-in laptop mic, USB headset): Use `MIC_TYPE: computer_mic` in config.yaml
- **Dynamic Mic** (XLR with audio interface): Use `MIC_TYPE: dynamic_mic` in config.yaml

**Verification**:
```bash
# List available audio devices
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"
```

**Audio Quality Tips**:
- Use a dedicated USB mic for better quality than built-in mics
- Position mic 6-12 inches from mouth
- Reduce background noise (close windows, turn off fans)
- Test with `arecord` (Linux) or `Voice Memos` (macOS) before running Agnus

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```ini
# Gemini API Key (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here
```

**Getting a Gemini API Key**:
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and paste into `.env`

**Security Notes**:
- Never commit `.env` to version control (already in .gitignore)
- Use restrictive file permissions: `chmod 600 .env`
- Rotate keys regularly (every 90 days recommended)
- Use different keys for development and production

### Configuration Files

**config.yaml** (Development settings):

```yaml
# Microphone type: "dynamic_mic" or "computer_mic"
MIC_TYPE: computer_mic

# Gemini model to use
GEMINI_MODEL: gemini-2.0-flash-live-001

# Voice for speech synthesis
# Options: Leda, Aoede, Puck, Charon, Kore
VOICE_NAME: Leda

# Video capture interval in seconds
# Lower = more frames, higher bandwidth
# Higher = fewer frames, lower bandwidth
VIDEO_CAPTURE_INTERVAL: 0.5

# Gradio UI title
WEB_UI_TITLE: Gemini Audio/Video Demo

# Gemini HTTP options
GEMINI_HTTP_OPTIONS:
  api_version: v1alpha

# Response modalities
GEMINI_RESPONSE_MODALITIES:
  - AUDIO
```

**media.yaml** (Media processing parameters):

```yaml
# Audio settings
INPUT_SAMPLE_RATE: 16000   # Hz, must match Gemini requirements
OUTPUT_SAMPLE_RATE: 24000  # Hz, Gemini speech output rate
AUDIO_FORMAT: 8            # pyaudio.paInt16
AUDIO_CHANNELS: 1          # mono

# Video settings
THUMBNAIL_MAX_SIZE: [1024, 1024]  # max frame dimensions
BLANK_IMAGE_DIMS: [480, 640, 3]   # placeholder image shape
```

**Performance Tuning**:
- Reduce `VIDEO_CAPTURE_INTERVAL` to 1.0 for lower bandwidth usage
- Reduce `THUMBNAIL_MAX_SIZE` to [640, 640] on slower networks
- Change `MIC_TYPE` if experiencing audio dropouts

---

## Local Development Deployment

### Quick Start

1. **Clone repository**:
   ```bash
   git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
   cd ECE-471-Generative-Machine-Learning/Final_Project
   ```

2. **Run setup script**:
   ```bash
   chmod +x setup.sh
   source ./setup.sh
   ```

   This creates `.venv/`, installs dependencies, and generates `.env.example`.

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Launch application**:
   ```bash
   python -m src.app
   ```

5. **Access UI**:
   Open browser to `http://127.0.0.1:7860/`

### Command-Line Options

```bash
# Run on custom port
python -m src.app --port 8080

# Create public shareable link (Gradio tunnel)
python -m src.app --share

# Enable debug logging
python -m src.app --debug

# Combine options
python -m src.app --port 8080 --share --debug
```

### Development Workflow

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Check code coverage
pytest --cov=src tests/

# Run specific test module
pytest tests/test_session_manager.py -v

# Run application with debug output
python -m src.app --debug

# Deactivate virtual environment when done
deactivate
```

---

## Production Deployment Options

### Option 1: Local Server (Simple)

Best for: Small teams, demos, controlled environments

**Setup**:
```bash
# Install as systemd service (Linux)
sudo nano /etc/systemd/system/agnus.service
```

**Service file** (`/etc/systemd/system/agnus.service`):
```ini
[Unit]
Description=Agnus Multimodal Agent
After=network.target

[Service]
Type=simple
User=agnus
Group=agnus
WorkingDirectory=/opt/agnus
Environment="PATH=/opt/agnus/.venv/bin"
ExecStart=/opt/agnus/.venv/bin/python -m src.app --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agnus
sudo systemctl start agnus
sudo systemctl status agnus
```

**Access**:
- Local: `http://localhost:7860`
- Network: `http://<server-ip>:7860` (configure firewall)

### Option 2: Cloud VM Deployment

Best for: Remote access, scalability, always-on availability

**Supported Platforms**:
- AWS EC2
- Google Compute Engine
- Azure Virtual Machines
- DigitalOcean Droplets

**Example: AWS EC2 Deployment**

1. **Launch EC2 instance**:
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.medium (2 vCPU, 4 GB RAM)
   - Storage: 20 GB gp3
   - Security group: Allow inbound TCP 7860 from your IP

2. **Connect and setup**:
   ```bash
   ssh -i your-key.pem ubuntu@<ec2-public-ip>

   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Python 3.11
   sudo apt install python3.11 python3.11-venv python3-pip git -y

   # Install camera/audio dependencies
   sudo apt install python3-opencv portaudio19-dev -y
   ```

3. **Deploy application**:
   ```bash
   # Clone repository
   git clone https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning.git
   cd ECE-471-Generative-Machine-Learning/Final_Project

   # Create virtual environment
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   nano .env  # Add GEMINI_API_KEY

   # Test run
   python -m src.app
   ```

4. **Setup systemd service** (see Option 1)

5. **Configure NGINX reverse proxy** (optional):
   ```nginx
   server {
       listen 80;
       server_name agnus.example.com;

       location / {
           proxy_pass http://127.0.0.1:7860;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

### Option 3: Docker Deployment

Best for: Containerized environments, Kubernetes clusters

**Dockerfile** (create in project root):
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    portaudio19-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Gradio port
EXPOSE 7860

# Run application
CMD ["python", "-m", "src.app", "--port", "7860"]
```

**Build and run**:
```bash
# Build image
docker build -t agnus:latest .

# Run container
docker run -d \
  --name agnus \
  --env-file .env \
  -p 7860:7860 \
  --device /dev/video0:/dev/video0 \
  --device /dev/snd:/dev/snd \
  agnus:latest

# View logs
docker logs -f agnus

# Stop container
docker stop agnus
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  agnus:
    build: .
    ports:
      - "7860:7860"
    env_file:
      - .env
    devices:
      - /dev/video0:/dev/video0
      - /dev/snd:/dev/snd
    restart: unless-stopped
    volumes:
      - ./output:/app/output
```

Run with: `docker-compose up -d`

### Option 4: Gradio Share Link

Best for: Quick demos, temporary sharing, no server setup

**Launch with share enabled**:
```bash
python -m src.app --share
```

**Output**:
```
Running on local URL:  http://127.0.0.1:7860
Running on public URL: https://abc123.gradio.live
```

**Characteristics**:
- Public URL valid for 72 hours
- Tunneled through Gradio's servers
- No server configuration needed
- Free for personal/educational use
- Not suitable for production (rate limits, uptime not guaranteed)

---

## Performance Optimization

### Network Optimization

**Bandwidth Usage**:
- Upload: ~120 KB/s (audio 16 KB/s + video 100 KB/s)
- Download: ~24 KB/s (speech audio)

**Reduce Bandwidth**:

1. **Lower video frame rate**:
   ```yaml
   # config.yaml
   VIDEO_CAPTURE_INTERVAL: 1.0  # Send 1 frame/sec instead of 2
   ```

2. **Reduce frame size**:
   ```yaml
   # media.yaml
   THUMBNAIL_MAX_SIZE: [640, 640]  # Smaller thumbnails
   ```

3. **Skip video entirely** (audio-only mode):
   Modify `src/core/media_loop.py` to disable `capture_video()` task

### Latency Optimization

**Reduce End-to-End Latency**:

Current typical latency: 500-1200ms

1. **Use smaller audio chunks** (dynamic mic):
   ```yaml
   # config.yaml
   MIC_TYPE: dynamic_mic  # 512 bytes instead of 1024
   ```

2. **Increase video interval**:
   ```yaml
   VIDEO_CAPTURE_INTERVAL: 1.0  # Less data = faster response
   ```

3. **Use faster Gemini model** (when available):
   ```yaml
   GEMINI_MODEL: gemini-2.0-flash-live-001  # Currently fastest
   ```

4. **Optimize network route**:
   - Use wired Ethernet instead of WiFi
   - Deploy server geographically close to users
   - Use low-latency DNS (Google 8.8.8.8, Cloudflare 1.1.1.1)

### CPU Optimization

**Reduce CPU Usage**:

1. **Lower frame rate** (see bandwidth optimization)

2. **Reduce frame resolution** before encoding:
   ```python
   # media_processing.py (advanced)
   # Reduce THUMBNAIL_MAX_SIZE in media.yaml
   ```

3. **Use hardware video encoding** (requires ffmpeg, advanced):
   Modify `encode_image_from_array()` to use h264 encoding

**Monitor CPU usage**:
```bash
# Linux
htop

# macOS
top -o cpu

# Python profiling
python -m cProfile -o profile.stats -m src.app
```

### Memory Optimization

**Reduce Memory Usage**:

1. **Limit audio queue size**:
   ```python
   # media_loop.py (line 67)
   self.audio_in_queue = asyncio.Queue(maxsize=10)  # Prevent unbounded growth
   ```

2. **Clear video frames** after sending:
   Already implemented in `capture_video()` - stores only `latest_video_frame`

3. **Monitor memory**:
   ```bash
   # Check memory usage
   ps aux | grep python

   # Python memory profiler
   pip install memory_profiler
   python -m memory_profiler src/app.py
   ```

---

## Security Best Practices

### API Key Security

1. **Never commit API keys**:
   - `.env` is in `.gitignore`
   - Always use `.env.example` as template

2. **Restrict API key permissions**:
   - In Google Cloud Console, restrict key to specific APIs
   - Set usage quotas to prevent abuse

3. **Rotate keys regularly**:
   ```bash
   # Generate new key in Google AI Studio
   # Update .env
   # Restart application
   sudo systemctl restart agnus
   ```

4. **Use key management services** (production):
   - AWS Secrets Manager
   - Google Secret Manager
   - Azure Key Vault

### Network Security

1. **Use firewall rules**:
   ```bash
   # Allow only specific IPs
   sudo ufw allow from 192.168.1.0/24 to any port 7860
   ```

2. **Enable HTTPS** with reverse proxy:
   - Use NGINX + Let's Encrypt for free SSL
   - Force HTTPS redirects

3. **Add authentication** to Gradio:
   ```python
   # src/ui/gradio_interface.py
   demo.launch(
       auth=("username", "password"),
       auth_message="Enter credentials to access Agnus"
   )
   ```

### Data Privacy

1. **No recording by default**:
   - Audio/video not saved to disk
   - Gemini session data subject to Google's privacy policy

2. **Enable logging carefully**:
   - Logs may contain PII
   - Store in `output/logs/` (gitignored)
   - Rotate logs regularly

3. **Compliance considerations**:
   - GDPR: Inform users about data processing
   - HIPAA: Agnus is NOT HIPAA-compliant (no PHI)
   - COPPA: Not suitable for children under 13

---

## Monitoring and Logging

### Application Logs

**Enable logging**:
```bash
# Redirect stdout/stderr to log file
python -m src.app > output/logs/app.log 2>&1
```

**Log rotation** (logrotate):
```
/opt/agnus/output/logs/app.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 agnus agnus
}
```

### Health Checks

**Monitor application health**:

```bash
# Check if Gradio is responding
curl -f http://localhost:7860/api/health || echo "Service DOWN"

# Check session status
curl http://localhost:7860/api/status
```

**Automated health check script** (`healthcheck.sh`):
```bash
#!/bin/bash
ENDPOINT="http://localhost:7860"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT)

if [ "$RESPONSE" != "200" ]; then
    echo "Health check FAILED: HTTP $RESPONSE"
    # Send alert (email, Slack, PagerDuty, etc.)
    exit 1
else
    echo "Health check OK"
    exit 0
fi
```

Run in cron: `*/5 * * * * /opt/agnus/healthcheck.sh`

### Metrics to Track

**System metrics**:
- CPU usage (should be <50% average)
- Memory usage (should be <2 GB)
- Network bandwidth (upload ~120 KB/s when active)
- Disk space (`output/` directory size)

**Application metrics**:
- Session start/stop events
- Active session duration
- Gemini API errors (rate limits, network failures)
- Audio queue depth (detect playback lag)
- Frame capture rate (detect camera issues)

**Prometheus integration** (advanced):
```python
# Add to src/core/session_manager.py
from prometheus_client import Counter, Gauge

sessions_started = Counter('agnus_sessions_started', 'Number of sessions started')
sessions_active = Gauge('agnus_sessions_active', 'Number of active sessions')

def start_media_session():
    # ... existing code ...
    sessions_started.inc()
    sessions_active.inc()
    # ...
```

---

## Backup and Recovery

### What to Back Up

**Critical files**:
- `.env` (API keys) - Store securely, encrypted
- `src/config/config.yaml` (custom settings)
- `src/config/media.yaml` (custom media params)
- `src/config/instructions.txt` (custom personality)

**Optional**:
- `output/logs/` (application logs)
- `output/recordings/` (if recording enabled)

**DO NOT back up**:
- `.venv/` (recreate with `pip install -r requirements.txt`)
- `__pycache__/` (generated at runtime)
- `tests/.pytest_cache/` (test artifacts)

### Backup Strategy

**Manual backup**:
```bash
# Create backup archive
tar -czf agnus-backup-$(date +%Y%m%d).tar.gz \
    .env \
    src/config/ \
    output/logs/ \
    output/recordings/

# Upload to S3 (example)
aws s3 cp agnus-backup-*.tar.gz s3://my-bucket/agnus-backups/
```

**Automated backup script** (`backup.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/agnus"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/agnus-$DATE.tar.gz \
    -C /opt/agnus \
    .env src/config/ output/

# Retain only last 7 backups
ls -t $BACKUP_DIR/agnus-*.tar.gz | tail -n +8 | xargs rm -f

echo "Backup completed: $BACKUP_DIR/agnus-$DATE.tar.gz"
```

Run daily: `0 2 * * * /opt/agnus/backup.sh`

### Disaster Recovery

**Restore from backup**:
```bash
# Extract backup
tar -xzf agnus-backup-20250104.tar.gz -C /opt/agnus/

# Recreate virtual environment
cd /opt/agnus
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart agnus
```

**Recovery Time Objective (RTO)**: ~15 minutes

**Recovery Point Objective (RPO)**: Last backup (daily recommended)

---

## Common Deployment Issues

### Issue: Port Already in Use

**Symptom**:
```
OSError: [Errno 48] Address already in use
```

**Solution**:
```bash
# Find process using port 7860
lsof -i :7860

# Kill process
kill -9 <PID>

# Or use different port
python -m src.app --port 8080
```

### Issue: Camera Not Detected

**Symptom**:
```
Cannot open camera
```

**Solution**:
```bash
# List available cameras
ls /dev/video*

# Test camera
python3 -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"

# Grant permissions (macOS)
# System Preferences → Security & Privacy → Camera → Allow Terminal

# Grant permissions (Linux)
sudo usermod -a -G video $USER
# Log out and back in
```

### Issue: Microphone Not Working

**Symptom**:
```
IOError: [Errno -9996] Invalid input device
```

**Solution**:
```bash
# List audio devices
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"

# Update config.yaml with correct MIC_TYPE
# Try both "computer_mic" and "dynamic_mic"

# Check system permissions (macOS)
# System Preferences → Security & Privacy → Microphone → Allow Terminal
```

### Issue: High Latency

**Symptom**: Delayed responses (>2 seconds)

**Solution**:
```bash
# Check network latency
ping google.com

# Reduce video frame rate
# Edit config.yaml: VIDEO_CAPTURE_INTERVAL: 1.0

# Check CPU usage
top -o cpu

# Use dynamic mic for smaller chunks
# Edit config.yaml: MIC_TYPE: dynamic_mic
```

### Issue: Gemini API Rate Limits

**Symptom**:
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Solution**:
1. Check quota in [Google Cloud Console](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas)
2. Request quota increase
3. Implement rate limiting in application (future enhancement)
4. Use different API key for testing vs. production

### Issue: Out of Memory

**Symptom**: Application crashes with `MemoryError`

**Solution**:
```bash
# Check memory usage
free -h

# Reduce frame size in media.yaml
THUMBNAIL_MAX_SIZE: [640, 640]

# Limit audio queue (edit src/core/media_loop.py line 67)
self.audio_in_queue = asyncio.Queue(maxsize=10)

# Add swap space (Linux)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Next Steps

After successful deployment:

1. **Monitor performance**: Track CPU, memory, bandwidth usage
2. **Test error scenarios**: Network interruption, camera failure, API errors
3. **Backup configuration**: Save `.env` and `src/config/` securely
4. **Set up alerts**: Email/Slack notifications for downtime
5. **Document customizations**: Keep notes on config changes

**Further Reading**:
- [Architecture Documentation](architecture.md) - System design details
- [API Reference](api_reference.md) - Function and class documentation
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [README](../README.md) - Project overview
