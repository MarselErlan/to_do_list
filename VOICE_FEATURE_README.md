# 🎤 Voice Assistant Feature - Complete Setup Guide

## Overview

The TaskFlow AI Voice Assistant allows users to create tasks using natural speech. It integrates with **LangSmith** for real-time monitoring and uses **LangGraph** for intelligent task processing.

## 🚀 Features

- **🎙️ Speech-to-Text**: Convert voice commands to text
- **🧠 AI Processing**: Intelligent task creation with LangGraph
- **📊 LangSmith Integration**: Real-time tracing and monitoring
- **🔐 JWT Authentication**: Secure WebSocket connections
- **👥 Team Context**: Multi-team task creation support
- **⚡ Real-time**: WebSocket-based communication

## 🛠️ Setup Instructions

### 1. Environment Configuration

Create or update your `.env` file with required settings:

```env
# Database
DATABASE_URL=sqlite:///./taskflow.db

# Core API Keys (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here
LANGCHAIN_API_KEY=lsv2_your-langsmith-api-key-here

# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=TaskFlow-Voice-Assistant

# Security
SECRET_KEY=your-secret-key-for-jwt-tokens

# Google Cloud (Optional - for enhanced voice features)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

### 2. Get Your API Keys

#### OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your `.env` file as `OPENAI_API_KEY`

#### LangSmith API Key

1. Visit [LangSmith](https://smith.langchain.com/)
2. Create an account and project
3. Go to Settings → API Keys
4. Create a new API key
5. Add it to your `.env` file as `LANGCHAIN_API_KEY`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

## 🔌 How to Connect

### Step 1: Authenticate User

Get a JWT token by authenticating:

```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Step 2: Connect to Voice WebSocket

```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."; // Your JWT token
const ws = new WebSocket(`ws://localhost:8000/ws/voice?token=${token}`);

ws.onopen = () => {
  console.log("🎤 Voice Assistant connected!");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("📨 Response:", data);
};
```

## 📱 Usage Examples

### Basic Voice Command

```javascript
// Send audio data (base64 encoded)
const audioData = "base64_encoded_audio_data_here";
ws.send(
  JSON.stringify({
    audio: audioData,
  })
);
```

### Set Session Context

```javascript
// Switch to a specific team/session
ws.send(
  JSON.stringify({
    session_name: "Marketing Team",
  })
);
```

### Complete Example

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Voice Assistant Test</title>
  </head>
  <body>
    <button id="startBtn">🎤 Start Recording</button>
    <button id="stopBtn">⏹️ Stop Recording</button>
    <div id="transcript"></div>
    <div id="response"></div>

    <script>
      const token = "YOUR_JWT_TOKEN_HERE";
      const ws = new WebSocket(`ws://localhost:8000/ws/voice?token=${token}`);

      let mediaRecorder;
      let audioChunks = [];

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.transcript) {
          document.getElementById(
            "transcript"
          ).innerHTML = `<strong>You said:</strong> ${data.transcript}`;
        }

        if (data.response_text) {
          document.getElementById(
            "response"
          ).innerHTML = `<strong>Assistant:</strong> ${data.response_text}`;
        }

        if (data.response) {
          // Play audio response
          const audio = new Audio(`data:audio/wav;base64,${data.response}`);
          audio.play();
        }
      };

      document.getElementById("startBtn").onclick = async () => {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.start();
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
          audioChunks.push(event.data);
        };
      };

      document.getElementById("stopBtn").onclick = () => {
        mediaRecorder.stop();

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
          const reader = new FileReader();

          reader.onload = () => {
            const base64Audio = reader.result.split(",")[1];
            ws.send(
              JSON.stringify({
                audio: base64Audio,
              })
            );
          };

          reader.readAsDataURL(audioBlob);
        };
      };
    </script>
  </body>
</html>
```

## 🎯 Voice Commands Examples

### Task Creation

- **"Create a task to call John at 3 PM"**
- **"Remind me to buy groceries tomorrow"**
- **"Schedule a meeting with the team next week"**
- **"Add a task to finish the report by Friday"**

### Team Tasks

- **"Create a team task for the marketing campaign"**
- **"Add a task for the development team"**
- **"Schedule a team meeting for tomorrow"**

### Greetings & Conversation

- **"Hello"** → Get friendly greeting
- **"How are you?"** → Conversational response
- **"Good morning"** → Time-appropriate greeting

## 📊 LangSmith Monitoring

### View Real-time Traces

1. Open [LangSmith Dashboard](https://smith.langchain.com/)
2. Navigate to your project: `TaskFlow-Voice-Assistant`
3. Monitor real-time traces for:
   - Voice transcription processing
   - LangGraph task parsing
   - Database operations
   - Response generation

### Key Metrics to Monitor

- **Latency**: Response time for voice commands
- **Success Rate**: Percentage of successful task creations
- **Error Rate**: Failed voice processing attempts
- **Token Usage**: OpenAI API consumption

## 🔧 Response Format

### Successful Task Creation

```json
{
  "transcript": "Create a task to call John at 3 PM",
  "response": "base64_encoded_audio_response",
  "response_text": "Task 'Call John' has been created successfully!",
  "llm_result": {
    "task_title": "Call John",
    "start_time": "15:00:00",
    "start_date": "2025-01-15",
    "is_complete": true
  }
}
```

### Clarification Needed

```json
{
  "transcript": "Create a task",
  "response": "base64_encoded_audio_response",
  "response_text": "What would you like the task to be about?",
  "llm_result": {
    "is_complete": false,
    "clarification_questions": ["What would you like the task to be about?"]
  }
}
```

### Interim Results

```json
{
  "interim_transcript": "Create a task to..."
}
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Error

```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL
```

**Solution:** Ensure `DATABASE_URL` is properly set in `.env`:

```env
DATABASE_URL=sqlite:///./taskflow.db
```

#### 2. Authentication Failed

```
WebSocket connection closed: 4001 Invalid token
```

**Solution:**

- Check JWT token is valid and not expired
- Ensure token is passed in URL: `ws://localhost:8000/ws/voice?token=YOUR_TOKEN`

#### 3. LangSmith Not Showing Traces

**Solution:**

- Verify `LANGCHAIN_API_KEY` is set correctly
- Check `LANGCHAIN_TRACING_V2=true` in `.env`
- Ensure project name matches in LangSmith dashboard

#### 4. Voice Not Processing

**Solution:**

- Check audio format (LINEAR16, 16kHz recommended)
- Ensure audio data is base64 encoded
- Verify microphone permissions in browser

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📋 API Endpoints

### WebSocket Endpoint

```
ws://localhost:8000/ws/voice?token=JWT_TOKEN
```

### Authentication Endpoint

```
POST /token
Content-Type: application/x-www-form-urlencoded
Body: username=user&password=pass
```

### Health Check

```
GET /health
```

## 🔒 Security Features

- **JWT Authentication**: All WebSocket connections require valid JWT tokens
- **User Context**: Tasks are created with proper user ownership
- **Session Isolation**: Users can only access their own teams/sessions
- **Input Validation**: All voice input is validated before processing

## 🎉 Getting Started Checklist

- [ ] Set up `.env` file with all required keys
- [ ] Start the server with `uvicorn app.main:app --reload`
- [ ] Create a user account and get JWT token
- [ ] Test WebSocket connection
- [ ] Send a voice command
- [ ] Check LangSmith dashboard for traces
- [ ] Verify task creation in database

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review LangSmith traces for detailed error information
3. Check server logs for additional debugging info

---

**🎤 Happy voice commanding! Your AI assistant is ready to help you stay organized!**
