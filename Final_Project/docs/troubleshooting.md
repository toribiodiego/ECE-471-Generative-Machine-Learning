# Troubleshooting Guide

This guide provides solutions to common issues encountered when running the Agnus multimodal agent. Issues are organized by category with diagnostic steps and solutions.

## Table of Contents

- [Audio Issues](#audio-issues)
- [Video Issues](#video-issues)
- [Network and API Issues](#network-and-api-issues)
- [Performance Issues](#performance-issues)
- [Configuration Issues](#configuration-issues)
- [Installation Issues](#installation-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Getting Additional Help](#getting-additional-help)

---

## Audio Issues

### Issue: No Audio Captured from Microphone

**Symptoms**:
- Application runs but Gemini doesn't respond to speech
- No visible errors in console
- Session appears to be running

**Diagnosis**:
```bash
# Test microphone capture
python3 -c "
import pyaudio
import sys

p = pyaudio.PyAudio()
try:
    stream = p.open(
        format=8,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )
    data = stream.read(1024)
    print('✓ Microphone working, captured {} bytes'.format(len(data)))
    stream.close()
except Exception as e:
    print('✗ Microphone error:', e)
finally:
    p.terminate()
"
```

**Solutions**:

1. **Check system permissions** (macOS):
   ```bash
   # System Preferences → Security & Privacy → Microphone
   # Ensure Terminal or Python has microphone access
   ```

2. **Check system permissions** (Linux):
   ```bash
   # Add user to audio group
   sudo usermod -a -G audio $USER
   # Log out and back in
   ```

3. **Verify correct input device**:
   ```bash
   # List all audio devices
   python3 -c "
   import pyaudio
   p = pyaudio.PyAudio()
   for i in range(p.get_device_count()):
       info = p.get_device_info_by_index(i)
       if info['maxInputChannels'] > 0:
           print(f'{i}: {info[\"name\"]} (inputs: {info[\"maxInputChannels\"]})')
   p.terminate()
   "
   ```

4. **Test with system tools**:
   ```bash
   # macOS: Use Voice Memos app
   # Linux: Test with arecord
   arecord -d 5 -f cd test.wav && aplay test.wav

   # Windows: Use Sound Recorder
   ```

### Issue: PyAudio Device Selection Error

**Symptoms**:
```
IOError: [Errno -9996] Invalid input device (no default output device)
OSError: [Errno -9997] Invalid sample rate
```

**Diagnosis**:
```bash
# Get default input device info
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
info = p.get_default_input_device_info()
print('Default input:', info['name'])
print('Sample rate:', info['defaultSampleRate'])
print('Channels:', info['maxInputChannels'])
p.terminate()
"
```

**Solutions**:

1. **Switch microphone type** in `config.yaml`:
   ```yaml
   # Try computer_mic instead of dynamic_mic
   MIC_TYPE: computer_mic
   ```

2. **Manually specify input device** (advanced):

   Edit `src/core/media_loop.py` line 81-89:
   ```python
   # Find your device index from the diagnosis above
   DEVICE_INDEX = 2  # Change to your device index

   self.audio_stream_in = await asyncio.to_thread(
       self.pya.open,
       format=self.config["AUDIO_FORMAT"],
       channels=self.config["AUDIO_CHANNELS"],
       rate=self.config["INPUT_SAMPLE_RATE"],
       input=True,
       input_device_index=DEVICE_INDEX,  # Explicit device
       frames_per_buffer=self.chunk_size,
   )
   ```

3. **Verify sample rate compatibility**:
   ```bash
   # Check if device supports 16kHz
   python3 -c "
   import pyaudio
   p = pyaudio.PyAudio()
   info = p.get_default_input_device_info()
   rate = 16000
   try:
       supported = p.is_format_supported(
           rate,
           input_device=info['index'],
           input_channels=1,
           input_format=8
       )
       print(f'✓ Device supports {rate}Hz')
   except ValueError as e:
       print(f'✗ Device does not support {rate}Hz')
       print(f'Default rate: {info[\"defaultSampleRate\"]}')
   p.terminate()
   "
   ```

### Issue: Audio Playback Choppy or Distorted

**Symptoms**:
- Gemini responds but audio is broken up
- Robotic or stuttering speech
- Audio cuts out intermittently

**Diagnosis**:
```bash
# Check audio queue depth (shows buffer backlog)
# Add debug logging to src/core/media_loop.py play_audio():
print(f"Queue size: {self.audio_in_queue.qsize()}")
```

**Solutions**:

1. **Increase buffer size**:

   Edit `src/core/media_loop.py` line 130-139:
   ```python
   # Increase chunk size for smoother playback
   self.audio_stream_out = await asyncio.to_thread(
       self.pya.open,
       format=self.config["AUDIO_FORMAT"],
       channels=self.config["AUDIO_CHANNELS"],
       rate=self.config["OUTPUT_SAMPLE_RATE"],
       output=True,
       frames_per_buffer=2048,  # Increased from 1024
   )
   ```

2. **Check CPU usage**:
   ```bash
   # High CPU can cause audio stuttering
   top -o cpu  # macOS
   htop        # Linux
   ```

3. **Close other audio applications**:
   - Spotify, iTunes, video players can interfere
   - Discord, Zoom can lock audio devices

4. **Reduce video frame rate** to free up bandwidth:
   ```yaml
   # config.yaml
   VIDEO_CAPTURE_INTERVAL: 1.0  # Send fewer frames
   ```

### Issue: No Audio Output (Gemini Silent)

**Symptoms**:
- Session running, microphone working
- Gemini processing requests (API calls succeed)
- No audio comes out of speakers

**Diagnosis**:
```bash
# Test speaker output
python3 -c "
import pyaudio
import numpy as np

p = pyaudio.PyAudio()
stream = p.open(
    format=8,
    channels=1,
    rate=24000,
    output=True,
    frames_per_buffer=1024
)

# Generate 1 second of test tone (440Hz)
samples = (np.sin(2 * np.pi * 440 * np.arange(24000) / 24000) * 32767).astype(np.int16)
stream.write(samples.tobytes())

stream.close()
p.terminate()
print('✓ If you heard a tone, speakers are working')
"
```

**Solutions**:

1. **Check system volume**:
   - Ensure volume is not muted
   - Increase volume to 50%+

2. **Verify output device**:
   ```bash
   # List output devices
   python3 -c "
   import pyaudio
   p = pyaudio.PyAudio()
   for i in range(p.get_device_count()):
       info = p.get_device_info_by_index(i)
       if info['maxOutputChannels'] > 0:
           print(f'{i}: {info[\"name\"]} (outputs: {info[\"maxOutputChannels\"]})')
   p.terminate()
   "
   ```

3. **Check Gemini response modality**:
   ```yaml
   # config.yaml
   GEMINI_RESPONSE_MODALITIES:
     - AUDIO  # Ensure this is set
   ```

---

## Video Issues

### Issue: Camera Not Detected

**Symptoms**:
```
Cannot open camera
[ERROR] OpenCV: Failed to open video capture device
```

**Diagnosis**:
```bash
# Test camera access
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('✓ Camera opened successfully')
    ret, frame = cap.read()
    if ret:
        print(f'✓ Captured frame: {frame.shape}')
    else:
        print('✗ Could not read frame')
    cap.release()
else:
    print('✗ Cannot open camera')
"
```

**Solutions**:

1. **Check camera permissions** (macOS):
   ```bash
   # System Preferences → Security & Privacy → Camera
   # Enable access for Terminal or Python
   ```

2. **Check camera is not in use**:
   ```bash
   # Close other apps using camera
   # Zoom, Skype, FaceTime, Photo Booth, etc.

   # List processes using camera (macOS)
   lsof | grep -i "camera\|video"

   # List video devices (Linux)
   ls -l /dev/video*
   v4l2-ctl --list-devices
   ```

3. **Try different camera index**:

   Edit `src/core/media_loop.py` line 175:
   ```python
   # Try camera index 1 instead of 0
   cap = cv2.VideoCapture(1)
   ```

4. **Verify camera hardware**:
   ```bash
   # macOS: Check in Photo Booth app
   # Linux: Test with cheese or guvcview
   sudo apt install cheese
   cheese

   # Windows: Test with Camera app
   ```

### Issue: Camera Permissions Denied (macOS)

**Symptoms**:
```
[ERROR] AVCaptureDeviceTypeExternal not authorized
[ERROR] Camera access denied
```

**Solution**:

1. **Grant camera permissions**:
   - System Preferences → Security & Privacy → Camera
   - Look for "Terminal" or "Python" in the list
   - Check the box to enable access
   - Restart terminal and try again

2. **Reset camera permissions** (if checkbox grayed out):
   ```bash
   # Reset all camera permissions
   tccutil reset Camera

   # Restart and try again
   ```

3. **Sign app** (for compiled Python apps):
   ```bash
   codesign --force --deep --sign - /path/to/python
   ```

### Issue: Camera Shows Black Screen

**Symptoms**:
- Camera opens successfully
- Video feed shows all black
- No error messages

**Diagnosis**:
```bash
# Capture test frame and save
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    cv2.imwrite('test_frame.jpg', frame)
    print('✓ Saved test_frame.jpg - check if it is black')
    print(f'Frame stats: min={frame.min()}, max={frame.max()}, mean={frame.mean():.1f}')
else:
    print('✗ Could not capture frame')
cap.release()
"
```

**Solutions**:

1. **Check camera lens cover**: Physical obstruction or privacy shutter

2. **Adjust camera settings**:
   ```bash
   # Linux: Use v4l2-ctl to adjust brightness
   v4l2-ctl -d /dev/video0 --set-ctrl=brightness=150
   ```

3. **Try different resolution**:
   ```python
   # Edit src/core/media_loop.py
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```

4. **Wait for camera to initialize**:
   ```python
   # Some cameras need warmup time
   import time
   cap = cv2.VideoCapture(0)
   time.sleep(2)  # Wait 2 seconds
   ret, frame = cap.read()
   ```

### Issue: Camera Video Lag or Low FPS

**Symptoms**:
- Video feed updates very slowly
- Significant delay between motion and display
- High CPU usage

**Solutions**:

1. **Reduce capture resolution**:
   ```python
   # Edit src/core/media_loop.py _capture_frame()
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```

2. **Increase capture interval**:
   ```yaml
   # config.yaml - capture less frequently
   VIDEO_CAPTURE_INTERVAL: 1.0  # 1 frame/sec instead of 2
   ```

3. **Reduce thumbnail size**:
   ```yaml
   # media.yaml
   THUMBNAIL_MAX_SIZE: [640, 640]  # Smaller than default 1024
   ```

4. **Check USB bandwidth** (for USB webcams):
   - Use USB 3.0 port instead of USB 2.0
   - Disconnect other USB devices
   - Avoid USB hubs

---

## Network and API Issues

### Issue: Gemini API Rate Limit Exceeded

**Symptoms**:
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded for quota metric 'Generate Content API requests per minute' and limit 'GenerateContentRequestsPerMinutePerProjectPerRegion'
```

**Diagnosis**:
```bash
# Check current quota usage
# Visit: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
```

**Solutions**:

1. **Request quota increase**:
   - Go to [Google Cloud Console Quotas](https://console.cloud.google.com/iam-admin/quotas)
   - Search for "Generative Language API"
   - Click on quota metric
   - Click "EDIT QUOTAS" and request increase
   - Typical limits: 60 requests/minute (free tier)

2. **Reduce request frequency**:
   ```yaml
   # config.yaml - send video less frequently
   VIDEO_CAPTURE_INTERVAL: 2.0  # Reduce from 0.5 to 2 seconds
   ```

3. **Implement rate limiting** (advanced):

   Edit `src/core/media_loop.py` to add request throttling:
   ```python
   import time

   class MediaLoop:
       def __init__(self, config):
           # ... existing code ...
           self.last_request_time = 0
           self.min_request_interval = 0.1  # Seconds between requests

       async def listen_audio(self):
           # ... existing code ...
           while not self.quit.is_set():
               data = await asyncio.to_thread(...)

               # Throttle requests
               now = time.time()
               if now - self.last_request_time >= self.min_request_interval:
                   await self.session.send_realtime_input(audio=blob)
                   self.last_request_time = now

               await asyncio.sleep(0)
   ```

4. **Use separate API keys** for dev and production:
   ```ini
   # .env.dev
   GEMINI_API_KEY=dev_key_here

   # .env.prod
   GEMINI_API_KEY=prod_key_here
   ```

### Issue: Gemini API Authentication Failed

**Symptoms**:
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
EnvironmentError: GEMINI_API_KEY not found in environment
```

**Diagnosis**:
```bash
# Check if .env file exists
ls -la .env

# Check if API key is set
grep GEMINI_API_KEY .env

# Test loading environment variables
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv('GEMINI_API_KEY')
if key:
    print(f'✓ API key loaded: {key[:10]}...')
else:
    print('✗ API key not found')
"
```

**Solutions**:

1. **Create .env file** if missing:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

2. **Verify .env format**:
   ```ini
   # Correct format (no spaces around =)
   GEMINI_API_KEY=your_actual_api_key_here

   # Wrong formats:
   # GEMINI_API_KEY = key    (spaces around =)
   # GEMINI_API_KEY="key"    (quotes not needed)
   # gemini_api_key=key      (wrong case)
   ```

3. **Check file permissions**:
   ```bash
   chmod 600 .env  # Read/write for owner only
   ```

4. **Verify API key is valid**:
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Check if key is still active
   - Generate new key if needed

### Issue: Network Connection Timeout

**Symptoms**:
```
requests.exceptions.ConnectionError: Connection timeout
TimeoutError: [Errno 60] Operation timed out
```

**Diagnosis**:
```bash
# Test internet connectivity
ping -c 4 google.com

# Test DNS resolution
nslookup generativelanguage.googleapis.com

# Test API endpoint reachability
curl -I https://generativelanguage.googleapis.com

# Check network latency
ping -c 10 generativelanguage.googleapis.com | tail -1
```

**Solutions**:

1. **Check firewall settings**:
   ```bash
   # Ensure outbound HTTPS (port 443) is allowed
   # Check corporate firewall/proxy settings
   ```

2. **Use different DNS server**:
   ```bash
   # macOS/Linux: Edit /etc/resolv.conf
   nameserver 8.8.8.8  # Google DNS
   nameserver 1.1.1.1  # Cloudflare DNS
   ```

3. **Configure proxy** (if behind corporate proxy):
   ```bash
   # .env
   HTTP_PROXY=http://proxy.company.com:8080
   HTTPS_PROXY=http://proxy.company.com:8080
   ```

4. **Increase timeout** (advanced):

   Edit `src/utils/gemini_client.py`:
   ```python
   http_options = {
       "api_version": "v1alpha",
       "timeout": 60  # Increase from default 30s
   }
   ```

---

## Performance Issues

### Issue: High Latency (Slow Response Time)

**Symptoms**:
- Response takes >2 seconds
- Noticeable delay between speaking and hearing response
- Laggy interaction

**Diagnosis**:
```bash
# Measure end-to-end latency
# Add timestamps to src/core/media_loop.py:
import time

async def listen_audio(self):
    while not self.quit.is_set():
        start = time.time()
        data = await asyncio.to_thread(...)
        await self.session.send_realtime_input(audio=blob)
        print(f"Audio sent: {(time.time() - start)*1000:.0f}ms")

async def play_audio(self):
    while not self.quit.is_set():
        data = await self.audio_in_queue.get()
        start = time.time()
        await asyncio.to_thread(self.audio_stream_out.write, data)
        print(f"Audio played: {(time.time() - start)*1000:.0f}ms")
```

**Solutions**:

1. **Use dynamic microphone** (smaller chunks):
   ```yaml
   # config.yaml
   MIC_TYPE: dynamic_mic  # 512 bytes instead of 1024
   ```

2. **Reduce video frame rate**:
   ```yaml
   # config.yaml
   VIDEO_CAPTURE_INTERVAL: 1.0  # Less data = faster processing
   ```

3. **Check network latency**:
   ```bash
   # Ping Gemini servers
   ping generativelanguage.googleapis.com

   # Target: <50ms for good performance
   # >100ms may cause noticeable delay
   ```

4. **Use wired connection** instead of WiFi:
   - Ethernet has lower latency than WiFi
   - Reduce interference from other devices

5. **Optimize audio settings**:
   ```yaml
   # media.yaml
   INPUT_SAMPLE_RATE: 16000   # Don't increase (Gemini requirement)
   OUTPUT_SAMPLE_RATE: 24000  # Don't increase
   ```

### Issue: High CPU Usage

**Symptoms**:
- CPU at 80-100%
- Fan running constantly
- System slowdown
- Audio/video stuttering

**Diagnosis**:
```bash
# Monitor CPU usage
top -o cpu  # macOS
htop        # Linux - shows per-core usage

# Profile Python application
python3 -m cProfile -o profile.stats -m src.app
python3 -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

**Solutions**:

1. **Reduce video processing**:
   ```yaml
   # config.yaml
   VIDEO_CAPTURE_INTERVAL: 2.0  # Capture less frequently

   # media.yaml
   THUMBNAIL_MAX_SIZE: [640, 640]  # Smaller frames
   ```

2. **Close background applications**:
   - Web browsers with many tabs
   - Video players, photo editors
   - Other Python processes

3. **Lower webcam resolution**:
   ```python
   # Edit src/core/media_loop.py capture_video()
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```

4. **Use hardware acceleration** (advanced):
   - Enable GPU encoding for video (requires ffmpeg)
   - Use Intel Quick Sync or NVENC if available

### Issue: High Memory Usage

**Symptoms**:
```
MemoryError: Unable to allocate array
OSError: [Errno 12] Cannot allocate memory
```

**Diagnosis**:
```bash
# Monitor memory usage
ps aux | grep python

# Python memory profiler
pip install memory_profiler
python3 -m memory_profiler src/app.py
```

**Solutions**:

1. **Limit audio queue size**:

   Edit `src/core/media_loop.py` line 67:
   ```python
   # Prevent unbounded queue growth
   self.audio_in_queue = asyncio.Queue(maxsize=20)
   ```

2. **Clear video frames after sending**:
   Already implemented - only `latest_video_frame` is kept

3. **Reduce frame size**:
   ```yaml
   # media.yaml
   THUMBNAIL_MAX_SIZE: [512, 512]  # Reduce from 1024
   ```

4. **Add swap space** (Linux):
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

---

## Configuration Issues

### Issue: Invalid MIC_TYPE Configuration

**Symptoms**:
```
ValueError: Invalid MIC_TYPE 'usb_mic'
```

**Solution**:

Edit `config.yaml` and use only valid values:
```yaml
# Valid options only:
MIC_TYPE: computer_mic  # or
MIC_TYPE: dynamic_mic
```

### Issue: Missing Configuration Files

**Symptoms**:
```
FileNotFoundError: Configuration file not found: src/config/config.yaml
```

**Diagnosis**:
```bash
# Check if config files exist
ls -la src/config/
```

**Solutions**:

1. **Verify project structure**:
   ```bash
   # Ensure you're in project root
   pwd
   ls src/config/  # Should show config.yaml, media.yaml, instructions.txt
   ```

2. **Restore missing files** from git:
   ```bash
   git checkout src/config/config.yaml
   git checkout src/config/media.yaml
   git checkout src/config/instructions.txt
   ```

### Issue: YAML Syntax Error

**Symptoms**:
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Diagnosis**:
```bash
# Validate YAML syntax
python3 -c "
import yaml
with open('src/config/config.yaml') as f:
    try:
        yaml.safe_load(f)
        print('✓ YAML is valid')
    except yaml.YAMLError as e:
        print('✗ YAML error:', e)
"
```

**Solutions**:

1. **Check indentation** (use spaces, not tabs):
   ```yaml
   # Correct:
   GEMINI_HTTP_OPTIONS:
     api_version: v1alpha

   # Wrong (mixed tabs/spaces):
   GEMINI_HTTP_OPTIONS:
   	api_version: v1alpha
   ```

2. **Quote special characters**:
   ```yaml
   # If value contains : or #
   VOICE_NAME: "Leda: Default"  # Must quote
   ```

3. **Use YAML validator**: https://www.yamllint.com/

---

## Installation Issues

### Issue: PyAudio Installation Failed

**Symptoms**:
```
error: portaudio.h: No such file or directory
ERROR: Failed building wheel for pyaudio
```

**Solutions**:

**macOS**:
```bash
brew install portaudio
pip install pyaudio
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**Linux (Fedora)**:
```bash
sudo dnf install portaudio-devel
pip install pyaudio
```

**Windows**:
```bash
# Download precompiled wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
pip install PyAudio‑0.2.11‑cp311‑cp311‑win_amd64.whl
```

### Issue: OpenCV Installation Failed

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement opencv-python
```

**Solutions**:

1. **Update pip**:
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install opencv-python
   ```

2. **Install system dependencies** (Linux):
   ```bash
   sudo apt-get install python3-opencv
   ```

3. **Use opencv-python-headless** (for servers without GUI):
   ```bash
   pip install opencv-python-headless
   ```

### Issue: Python Version Incompatibility

**Symptoms**:
```
SyntaxError: invalid syntax (TaskGroup not supported)
ImportError: cannot import name 'TaskGroup' from 'asyncio'
```

**Solution**:

Agnus requires Python 3.11+ for `asyncio.TaskGroup`:

```bash
# Check Python version
python3 --version

# Install Python 3.11 (Ubuntu)
sudo apt-get install python3.11 python3.11-venv

# Install Python 3.11 (macOS)
brew install python@3.11

# Recreate virtual environment with correct version
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Platform-Specific Issues

### macOS: Code Signing Issues

**Symptoms**:
```
'python' cannot be opened because the developer cannot be verified
```

**Solution**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /path/to/python

# Or allow in System Preferences → Security & Privacy
```

### Linux: Permission Denied for Camera/Mic

**Symptoms**:
```
Permission denied: '/dev/video0'
Permission denied: '/dev/snd/*'
```

**Solutions**:

1. **Add user to groups**:
   ```bash
   sudo usermod -a -G video $USER
   sudo usermod -a -G audio $USER
   # Log out and back in
   ```

2. **Check udev rules** (for USB devices):
   ```bash
   ls -l /dev/video*
   # Should show group ownership as 'video'
   ```

3. **Run as root** (not recommended):
   ```bash
   sudo python3 -m src.app
   ```

### Windows: DLL Load Failed

**Symptoms**:
```
ImportError: DLL load failed while importing _portaudio
```

**Solutions**:

1. **Install Visual C++ Redistributable**:
   - Download from [Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)
   - Install and restart

2. **Add PATH to portaudio DLL**:
   ```bash
   # Find portaudio DLL location
   python -c "import pyaudio; print(pyaudio.__file__)"
   # Add that directory to System PATH
   ```

---

## Getting Additional Help

### Collecting Debug Information

When reporting issues, collect this information:

```bash
# System information
python3 --version
uname -a  # Linux/macOS
systeminfo  # Windows

# Python packages
pip list

# Configuration
cat src/config/config.yaml
cat src/config/media.yaml
# (redact API keys!)

# Audio devices
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i))
p.terminate()
"

# Video devices
python3 -c "
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'Camera {i}: opened')
        cap.release()
"

# Run with debug output
python3 -m src.app --debug > debug.log 2>&1
```

### Viewing Application Logs

```bash
# If running as systemd service
journalctl -u agnus -f

# If running manually
python3 -m src.app 2>&1 | tee app.log
```

### Testing in Isolation

Test each component separately:

1. **Test configuration loading**:
   ```bash
   python3 -c "
   from src.utils.config_loader import load_config
   config = load_config()
   print('✓ Config loaded:', len(config), 'keys')
   "
   ```

2. **Test microphone capture**:
   ```bash
   python3 -c "
   import pyaudio
   p = pyaudio.PyAudio()
   stream = p.open(format=8, channels=1, rate=16000, input=True, frames_per_buffer=1024)
   data = stream.read(1024)
   print('✓ Captured', len(data), 'bytes')
   stream.close()
   p.terminate()
   "
   ```

3. **Test camera capture**:
   ```bash
   python3 -c "
   import cv2
   cap = cv2.VideoCapture(0)
   ret, frame = cap.read()
   if ret:
       print('✓ Captured frame:', frame.shape)
   cap.release()
   "
   ```

4. **Test Gemini API connection**:
   ```bash
   python3 -c "
   from dotenv import load_dotenv
   import os
   from src.utils.gemini_client import get_gemini_client

   load_dotenv()
   api_key = os.getenv('GEMINI_API_KEY')
   client = get_gemini_client(api_key, {'api_version': 'v1alpha'})
   print('✓ Gemini client initialized')
   "
   ```

### Resources

- **GitHub Issues**: [Report bugs and request features](https://github.com/toribiodiego/ECE-471-Generative-Machine-Learning/issues)
- **Documentation**:
  - [README](../README.md) - Project overview
  - [Architecture Guide](architecture.md) - System design
  - [API Reference](api_reference.md) - Function documentation
  - [Deployment Guide](deployment_guide.md) - Production setup
- **Gemini API Docs**: [Official documentation](https://ai.google.dev/gemini-api/docs)
- **PyAudio Docs**: [PortAudio documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- **OpenCV Docs**: [Python tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)

### Community Support

When asking for help:
1. Describe what you're trying to do
2. Show exact error messages (full stack trace)
3. Share your configuration (redact API keys)
4. Mention your OS and Python version
5. List steps you've already tried

**Example good issue report**:
```
Title: Camera opens but shows black screen on macOS 13.4

Environment:
- macOS 13.4 (Ventura)
- Python 3.11.4
- opencv-python 4.8.0

Steps to reproduce:
1. Run: python3 -m src.app
2. Click Start button
3. Camera light turns on but feed shows all black

What I've tried:
- Tested camera in Photo Booth (works)
- Granted camera permissions in System Preferences
- Tried VIDEO_CAPTURE_INTERVAL: 1.0
- test_frame.jpg shows all zeros (completely black)

Error output:
[Include relevant logs]
```

---

## Quick Reference: Diagnostic Commands

```bash
# Audio
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]; p.terminate()"

# Video
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAILED'); cap.release()"

# API Key
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OK' if os.getenv('GEMINI_API_KEY') else 'MISSING')"

# Network
ping -c 4 generativelanguage.googleapis.com

# Config
python3 -c "from src.utils.config_loader import load_config; print(f'OK: {len(load_config())} keys')"

# Full health check
python3 -c "
from src.utils.config_loader import load_config
from dotenv import load_dotenv
import os, pyaudio, cv2

load_dotenv()

print('Config:', 'OK' if load_config() else 'FAIL')
print('API Key:', 'OK' if os.getenv('GEMINI_API_KEY') else 'FAIL')

p = pyaudio.PyAudio()
print('Audio:', 'OK' if p.get_device_count() > 0 else 'FAIL')
p.terminate()

cap = cv2.VideoCapture(0)
print('Video:', 'OK' if cap.isOpened() else 'FAIL')
cap.release()
"
```
