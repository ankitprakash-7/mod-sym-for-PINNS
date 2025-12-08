# 🚀 Quick Start Guide

Get the React Code Editor API running in 5 minutes!

## Step 1: Setup Environment

```bash
# Navigate to project directory
cd react-code-editor

# Copy environment file
cp .env.example .env

# Edit .env for LOCAL TESTING MODE
nano .env
```

Set these values in `.env`:
```env
USE_LOCAL_FILES=true
LOCAL_FILES_PATH=/tmp/react-code-editor/sample_app
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Start the API

```bash
python app.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ✅ API initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Test the API

In a new terminal:

```bash
# Make test script executable
chmod +x test_api.py

# Run health check
curl http://localhost:8000/health

# Run test script
python test_api.py
```

Or test with a custom instruction:
```bash
python test_api.py "Change the Play button color to red"
```

## Example API Calls

### Using cURL

```bash
curl -X POST http://localhost:8000/edit \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "test-app",
    "msg_id": "v1",
    "instruction": "Make the title text bigger and bold"
  }'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/edit",
    json={
        "app_id": "test-app",
        "msg_id": "v1",
        "instruction": "Add a Delete button below the volume control"
    }
)

print(response.json())
```

### Using JavaScript

```javascript
fetch('http://localhost:8000/edit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    app_id: 'test-app',
    msg_id: 'v1',
    instruction: 'Change the background gradient colors'
  })
})
.then(res => res.json())
.then(data => console.log(data))
```

## Try These Instructions

Simple edits:
- "Change the Play button color to green"
- "Make the song title larger"
- "Add a red Delete button below the playlist"

Complex edits:
- "Add a search box above the playlist to filter songs"
- "Create a dark mode toggle button in the header"
- "Add a like button (heart icon) to each playlist item"

With new packages:
- "Add a progress bar using react-circular-progressbar"
- "Add smooth animations using framer-motion"
- "Add a notification toast using react-hot-toast"

## Check the Logs

```bash
# Watch logs in real-time
tail -f react_editor.log

# Search for errors
grep ERROR react_editor.log

# View Phase 1 file selections
grep "Phase 1" react_editor.log
```

## API Documentation

Open in browser:
```
http://localhost:8000/docs
```

This opens the interactive Swagger UI where you can:
- Test endpoints directly
- See request/response schemas
- Try different instructions

## Troubleshooting

**API won't start:**
- Check Python version: `python --version` (need 3.9+)
- Verify dependencies: `pip list`
- Check port 8000 is free: `lsof -i :8000`

**Health check fails:**
- Ensure API is running: `ps aux | grep app.py`
- Check logs: `tail react_editor.log`

**Edit fails:**
- Check `.env` has correct LOCAL_FILES_PATH
- Verify sample_app exists: `ls sample_app/`
- Check logs for details: `grep ERROR react_editor.log`

## Next Steps

1. **Try different instructions** - The API understands natural language!
2. **Check the modified files** - They're in the temp directory during processing
3. **Review logs** - See how file selection works
4. **Connect to GCS** - Switch to production mode when ready

## Production Setup

To use with Google Cloud Storage:

1. Create GCS buckets:
```bash
gsutil mb gs://prompttoapp-codefiles
gsutil mb gs://prompttoapp-codefolders
```

2. Get service account key and update `.env`:
```env
USE_LOCAL_FILES=false
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

3. Upload an app:
```bash
# Upload zip to: gs://prompttoapp-codefolders/{app_id}/{msg_id}.zip
gsutil cp my-app.zip gs://prompttoapp-codefolders/my-app/v1.zip
```

4. Edit the app:
```bash
curl -X POST http://localhost:8000/edit \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "my-app",
    "msg_id": "v1",
    "instruction": "Add a search feature"
  }'
```

## Support

- 📖 Full docs: `README.md`
- 🔍 API docs: http://localhost:8000/docs
- 📋 Logs: `react_editor.log`
- 💬 Test script: `python test_api.py`

Happy coding! 🎉
