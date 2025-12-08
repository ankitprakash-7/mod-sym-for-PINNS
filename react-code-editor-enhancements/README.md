# 🚀 React Code Editor API

AI-powered React code editing microservice using a two-phase LLM approach for intelligent, cost-effective modifications.

## 📋 Features

- **Two-Phase LLM Architecture**: Intelligent file selection + focused editing
- **Smart Package Management**: Automatic dependency detection and updates
- **Fast Metadata Extraction**: No LLM calls for code analysis (~100ms)
- **Cost-Effective**: ~$0.05 per edit (10x cheaper than full context)
- **Cloud-Native**: Integrated with Google Cloud Storage
- **Local Testing**: Test without GCS using local files

## 🏗️ Architecture

```
User Instruction
      ↓
1. Download App (GCS)
      ↓
2. Extract Metadata (Fast, No LLM)
   - Component analysis
   - File tree generation
   - Dependency mapping
      ↓
3. Phase 1: Select Files (LLM)
   Input: Instruction + Metadata
   Output: List of relevant files
   Cost: ~$0.001, Time: 1-2s
      ↓
4. Load Selected Files
   Only 2-7 files instead of all files
      ↓
5. Phase 2: Generate Edits (LLM)
   Input: Instruction + Selected Files + Context
   Output: Modified code
   Cost: ~$0.05, Time: 3-5s
      ↓
6. Update Packages
   Auto-detect and add missing dependencies
      ↓
7. Upload to GCS
   Both unzipped and zip formats
```

## 🔧 Setup

### Prerequisites

- Python 3.9+
- Google Cloud account with:
  - Cloud Storage buckets
  - Vertex AI enabled
  - Service account key

### 1. Install Dependencies

```bash
cd react-code-editor
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# For GCS Mode
USE_LOCAL_FILES=false
GCS_CODE_FILES_BUCKET=prompttoapp-codefiles
GCS_CODE_FOLDERS_BUCKET=prompttoapp-codefolders
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# For Local Testing Mode
USE_LOCAL_FILES=true
LOCAL_FILES_PATH=/tmp/react-code-editor/sample_app
```

### 3. Setup Google Cloud (if using GCS)

```bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Create buckets (if they don't exist)
gsutil mb gs://prompttoapp-codefiles
gsutil mb gs://prompttoapp-codefolders
```

## 🚀 Running the Service

### Local Testing Mode (No GCS Required)

```bash
# Set local mode in .env
USE_LOCAL_FILES=true
LOCAL_FILES_PATH=/tmp/react-code-editor/sample_app

# Run the service
python app.py
```

The API will be available at: `http://localhost:8000`

### Production Mode (with GCS)

```bash
# Set GCS mode in .env
USE_LOCAL_FILES=false

# Run the service
python app.py

# Or with uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Endpoints

### POST `/edit`

Edit a React application based on natural language instruction.

**Request Body:**

```json
{
  "app_id": "my-react-app",
  "msg_id": "v1",
  "instruction": "Change the Play button color to green in the music player"
}
```

**Response:**

```json
{
  "success": true,
  "message": "App edited successfully",
  "files_modified": ["src/components/MusicPlayer.jsx"],
  "files_added": [],
  "packages_added": [],
  "explanation": "Changed button background color from blue to green in MusicPlayer component",
  "debug_info": {
    "selected_files_count": 2,
    "estimated_scope": "small",
    "confidence": "high"
  }
}
```

### GET `/health`

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "service": "React Code Editor API",
  "version": "2.0.0",
  "local_mode": true
}
```

## 🧪 Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Edit request
curl -X POST http://localhost:8000/edit \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "test-app",
    "msg_id": "v1",
    "instruction": "Add a red Delete button below the Play button"
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
        "instruction": "Change the app title to 'My Music Player'"
    }
)

result = response.json()
print(result)
```

## 📦 Sample App Structure

The service expects React apps with this structure:

```
app/
├── package.json          # Required
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── public/
│   └── assets/
└── src/
    ├── App.jsx          # Main component
    ├── main.jsx
    ├── index.css
    └── components/
        ├── MusicPlayer.jsx
        └── Playlist.jsx
```

## 🎯 Example Instructions

The API understands natural language instructions:

**Simple Edits:**
- "Change the Play button color to green"
- "Add a Delete button next to the Edit button"
- "Make the title text larger"

**Complex Edits:**
- "Add a bar chart showing user activity"
- "Implement a search feature that filters the playlist"
- "Add dark mode toggle functionality"

**With New Packages:**
- "Add a calendar component using react-datepicker"
- "Create an animated loading spinner using framer-motion"
- "Add form validation using react-hook-form"

## 🔍 How It Works

### Metadata Extraction (Fast, No LLM)

The service analyzes code files to extract:
- Component names and types
- React hooks used
- Import statements
- External packages
- JSX elements count
- Event handlers
- State variables

### Phase 1: File Selection (LLM)

Input to LLM:
- User instruction
- File summaries (1-2 lines each)
- File tree structure
- Component relationships

Output from LLM:
```json
{
  "files_needed": [
    {
      "path": "src/components/MusicPlayer.jsx",
      "reason": "Contains the Play button mentioned in instruction"
    }
  ],
  "estimated_scope": "small",
  "requires_new_packages": false,
  "confidence": "high"
}
```

### Phase 2: Code Editing (LLM)

Input to LLM:
- User instruction
- Full content of selected files
- File tree for context
- Component relationships
- Current dependencies

Output from LLM:
```
MODIFIED_FILE_START: src/components/MusicPlayer.jsx
[Complete modified file content]
MODIFIED_FILE_END: src/components/MusicPlayer.jsx

EXPLANATION: Changed button background from blue-500 to green-500
```

### Automatic Package Management

After code editing:
1. Parse all imports from modified files
2. Compare with existing package.json
3. Auto-add missing packages with appropriate versions
4. Update package.json

Example:
```javascript
// LLM adds this import
import { BarChart } from 'recharts';

// Service automatically adds to package.json:
"recharts": "^2.12.7"
```

## 📊 Performance

| Metric | Value |
|--------|-------|
| Total Time | 5-10 seconds |
| Phase 1 Cost | ~$0.001 |
| Phase 2 Cost | ~$0.05 |
| Total Cost | ~$0.051 per edit |
| Token Usage | ~10K tokens total |

Compare to sending all files:
- Old: 50K-100K tokens, $0.50, 15-30s
- New: 10K tokens, $0.05, 5-10s
- **Improvement: 10x cheaper, 3x faster**

## 🐛 Troubleshooting

### Error: "Message ID not found"

The specified msg_id doesn't exist in GCS. Check:
- Correct app_id and msg_id
- File exists at `gs://prompttoapp-codefolders/{app_id}/{msg_id}.zip`

### Error: "No files were successfully loaded"

Files selected by Phase 1 don't exist. This may indicate:
- App structure is unusual
- LLM selected incorrect paths
- Check logs for file selection details

### Error: "Invalid JSON response from LLM"

Phase 1 LLM didn't return proper JSON. The service will use fallback selection.

### Validation Warnings

If you see validation warnings like "unbalanced braces", the generated code may have syntax issues. The service will still save the files, but you should review them.

## 📝 Logging

Logs are written to:
- Console (stdout)
- `react_editor.log` file

Log levels:
- INFO: Main process steps
- DEBUG: Detailed information
- WARNING: Non-critical issues
- ERROR: Failures

## 🔐 Security

- Service account key should have minimal permissions
- Only grant access to specific GCS buckets
- Never commit `.env` or service account keys to git
- Use separate buckets for different environments

## 🚀 Deployment

### Docker (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t react-editor-api .
docker run -p 8000:8000 --env-file .env react-editor-api
```

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/react-editor-api

# Deploy
gcloud run deploy react-editor-api \
  --image gcr.io/PROJECT_ID/react-editor-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=PROJECT_ID
```

## 📚 Project Structure

```
react-code-editor/
├── app.py                    # Main FastAPI service
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── README.md                # This file
├── react_editor.log         # Service logs
├── utils/
│   ├── __init__.py
│   ├── gcs_manager.py       # GCS operations
│   ├── metadata_extractor.py # Fast code analysis
│   ├── llm_client.py        # Two-phase LLM
│   ├── package_manager.py   # Dependency detection
│   └── response_parser.py   # Parse LLM responses
└── sample_app/              # Sample React app for testing
    ├── package.json
    ├── vite.config.js
    └── src/
        └── ...
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 💡 Tips

- Start with small, specific instructions for best results
- The service works best with standard React + Vite + Tailwind apps
- Package detection is automatic - no need to mention packages in instructions
- Check logs for detailed information about file selection and editing
- Use local mode for rapid development and testing

## 🆘 Support

For issues or questions:
1. Check the logs: `react_editor.log`
2. Review the troubleshooting section
3. Enable debug logging in `.env`: `LOG_LEVEL=DEBUG`
4. Check the API documentation: `http://localhost:8000/docs`
