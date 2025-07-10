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

## 🎤 **NEW: Continuous Voice Chat (Like ChatGPT)**

### Enhanced Voice Assistant with VAD and Continuous Listening

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Continuous Voice Chat</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
      }
      .chat-container {
        height: 400px;
        overflow-y: auto;
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
      }
      .message {
        margin: 10px 0;
        padding: 10px;
        border-radius: 10px;
      }
      .user-message {
        background-color: #007bff;
        color: white;
        text-align: right;
      }
      .assistant-message {
        background-color: #e9ecef;
        color: black;
      }
      .status {
        text-align: center;
        margin: 20px 0;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
      }
      .listening {
        background-color: #28a745;
        color: white;
      }
      .speaking {
        background-color: #ffc107;
        color: black;
      }
      .processing {
        background-color: #17a2b8;
        color: white;
      }
      .idle {
        background-color: #6c757d;
        color: white;
      }
      .controls {
        text-align: center;
        margin: 20px 0;
      }
      button {
        padding: 15px 30px;
        font-size: 16px;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        margin: 5px;
      }
      .start-btn {
        background-color: #28a745;
        color: white;
      }
      .stop-btn {
        background-color: #dc3545;
        color: white;
      }
      .volume-indicator {
        width: 100%;
        height: 20px;
        background-color: #e9ecef;
        border-radius: 10px;
        overflow: hidden;
        margin: 10px 0;
      }
      .volume-level {
        height: 100%;
        background-color: #28a745;
        transition: width 0.1s ease;
      }
    </style>
  </head>
  <body>
    <h1>🎤 Continuous Voice Chat Assistant</h1>

    <div class="status idle" id="status">Ready to start voice chat</div>

    <div class="volume-indicator">
      <div class="volume-level" id="volumeLevel"></div>
    </div>

    <div class="controls">
      <button class="start-btn" id="startVoiceChat">🎤 Start Voice Chat</button>
      <button class="stop-btn" id="stopVoiceChat">⏹️ Stop Voice Chat</button>
    </div>

    <div class="chat-container" id="chatContainer">
      <div class="message assistant-message">
        👋 Hello! I'm your voice assistant. Click "Start Voice Chat" and just
        start talking - I'll automatically detect when you're speaking and
        respond when you're done.
      </div>
    </div>

    <script>
      class ContinuousVoiceChat {
        constructor() {
          this.token = "YOUR_JWT_TOKEN_HERE"; // Replace with actual token
          this.ws = null;
          this.mediaRecorder = null;
          this.audioStream = null;
          this.audioContext = null;
          this.analyser = null;
          this.isListening = false;
          this.isProcessing = false;
          this.isSpeaking = false;
          this.currentAudio = null;

          // VAD parameters
          this.vadThreshold = 0.01; // Voice activity detection threshold
          this.silenceThreshold = 1500; // ms of silence before processing
          this.volumeThreshold = 0.005; // Minimum volume to consider as speech

          // Timers
          this.silenceTimer = null;
          this.vadTimer = null;

          // Audio data buffer
          this.audioBuffer = [];
          this.isRecording = false;

          this.initializeUI();
          this.setupWebSocket();
        }

        initializeUI() {
          document.getElementById("startVoiceChat").onclick = () =>
            this.startVoiceChat();
          document.getElementById("stopVoiceChat").onclick = () =>
            this.stopVoiceChat();
        }

        setupWebSocket() {
          this.ws = new WebSocket(
            `ws://localhost:8000/ws/voice?token=${this.token}`
          );

          this.ws.onopen = () => {
            console.log("🎤 Voice Chat connected!");
            this.updateStatus("Connected - Ready to chat", "idle");
          };

          this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
          };

          this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            this.updateStatus("Connection error", "idle");
          };

          this.ws.onclose = () => {
            console.log("WebSocket closed");
            this.updateStatus("Disconnected", "idle");
          };
        }

        async startVoiceChat() {
          try {
            // Get microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({
              audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000,
              },
            });

            // Setup audio context for VAD
            this.audioContext = new (window.AudioContext ||
              window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;

            const source = this.audioContext.createMediaStreamSource(
              this.audioStream
            );
            source.connect(this.analyser);

            // Setup media recorder
            this.mediaRecorder = new MediaRecorder(this.audioStream, {
              mimeType: "audio/webm;codecs=opus",
            });

            this.mediaRecorder.ondataavailable = (event) => {
              if (event.data.size > 0) {
                this.audioBuffer.push(event.data);
              }
            };

            this.mediaRecorder.onstop = () => {
              this.processAudioBuffer();
            };

            // Start continuous listening
            this.isListening = true;
            this.updateStatus("Listening... Start talking", "listening");
            this.startVoiceActivityDetection();
          } catch (error) {
            console.error("Error starting voice chat:", error);
            this.updateStatus("Microphone access denied", "idle");
          }
        }

        stopVoiceChat() {
          this.isListening = false;

          // Stop all audio processing
          if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
            this.mediaRecorder.stop();
          }

          // Stop current audio playback
          if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
          }

          // Clean up audio resources
          if (this.audioStream) {
            this.audioStream.getTracks().forEach((track) => track.stop());
          }

          if (this.audioContext) {
            this.audioContext.close();
          }

          // Clear timers
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
          }
          if (this.vadTimer) {
            clearTimeout(this.vadTimer);
          }

          this.updateStatus("Voice chat stopped", "idle");
        }

        startVoiceActivityDetection() {
          if (!this.isListening) return;

          const bufferLength = this.analyser.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);

          const checkAudioLevel = () => {
            if (!this.isListening) return;

            this.analyser.getByteFrequencyData(dataArray);

            // Calculate volume level
            const average =
              dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
            const volumeLevel = average / 255;

            // Update volume indicator
            document.getElementById("volumeLevel").style.width = `${
              volumeLevel * 100
            }%`;

            // Voice activity detection
            if (
              volumeLevel > this.volumeThreshold &&
              !this.isProcessing &&
              !this.isSpeaking
            ) {
              this.onVoiceDetected();
            } else if (
              volumeLevel <= this.volumeThreshold &&
              this.isRecording
            ) {
              this.onSilenceDetected();
            }

            // Continue monitoring
            requestAnimationFrame(checkAudioLevel);
          };

          checkAudioLevel();
        }

        onVoiceDetected() {
          if (this.isRecording) return;

          // Stop any current assistant speech
          if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
            this.isSpeaking = false;
          }

          // Clear silence timer
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
          }

          // Start recording
          this.isRecording = true;
          this.audioBuffer = [];
          this.mediaRecorder.start();
          this.updateStatus("🎤 Listening to you...", "listening");

          console.log("Voice detected - started recording");
        }

        onSilenceDetected() {
          if (!this.isRecording) return;

          // Clear existing silence timer
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
          }

          // Set new silence timer
          this.silenceTimer = setTimeout(() => {
            this.stopRecordingAndProcess();
          }, this.silenceThreshold);
        }

        stopRecordingAndProcess() {
          if (!this.isRecording) return;

          this.isRecording = false;
          this.mediaRecorder.stop();
          this.updateStatus("🧠 Processing your message...", "processing");

          console.log("Silence detected - stopped recording");
        }

        processAudioBuffer() {
          if (this.audioBuffer.length === 0) {
            this.updateStatus("Listening... Start talking", "listening");
            return;
          }

          // Combine audio chunks
          const audioBlob = new Blob(this.audioBuffer, {
            type: "audio/webm;codecs=opus",
          });
          const reader = new FileReader();

          reader.onload = () => {
            const base64Audio = reader.result.split(",")[1];

            // Send to backend
            this.ws.send(
              JSON.stringify({
                audio: base64Audio,
                continuous_mode: true,
              })
            );

            this.isProcessing = true;
          };

          reader.readAsDataURL(audioBlob);
        }

        handleWebSocketMessage(data) {
          if (data.transcript) {
            this.addMessage(data.transcript, "user");
          }

          if (data.response_text) {
            this.addMessage(data.response_text, "assistant");

            // Play audio response
            if (data.response) {
              this.playAudioResponse(data.response);
            } else {
              // If no audio, go back to listening
              this.isProcessing = false;
              this.updateStatus("Listening... Start talking", "listening");
            }
          }

          if (data.error) {
            this.addMessage(`Error: ${data.error}`, "assistant");
            this.isProcessing = false;
            this.updateStatus("Listening... Start talking", "listening");
          }
        }

        playAudioResponse(base64Audio) {
          this.isSpeaking = true;
          this.updateStatus("🤖 Assistant is speaking...", "speaking");

          this.currentAudio = new Audio(`data:audio/wav;base64,${base64Audio}`);

          this.currentAudio.onended = () => {
            this.isSpeaking = false;
            this.isProcessing = false;
            this.currentAudio = null;
            this.updateStatus("Listening... Start talking", "listening");
          };

          this.currentAudio.onerror = () => {
            this.isSpeaking = false;
            this.isProcessing = false;
            this.currentAudio = null;
            this.updateStatus("Listening... Start talking", "listening");
          };

          this.currentAudio.play();
        }

        addMessage(text, sender) {
          const chatContainer = document.getElementById("chatContainer");
          const messageDiv = document.createElement("div");
          messageDiv.className = `message ${sender}-message`;
          messageDiv.textContent = text;
          chatContainer.appendChild(messageDiv);
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        updateStatus(message, type) {
          const statusElement = document.getElementById("status");
          statusElement.textContent = message;
          statusElement.className = `status ${type}`;
        }
      }

      // Initialize when page loads
      document.addEventListener("DOMContentLoaded", () => {
        new ContinuousVoiceChat();
      });
    </script>
  </body>
</html>
```

### Key Features of Continuous Voice Chat:

1. **🎤 Voice Activity Detection (VAD)**: Automatically detects when you start speaking
2. **🔇 Silence Detection**: Processes your speech when you stop talking
3. **🛑 Interrupt Capability**: Can interrupt the assistant while it's speaking
4. **📊 Volume Indicator**: Visual feedback of voice levels
5. **💬 Chat Interface**: Shows conversation history
6. **🔄 Continuous Loop**: Seamless back-and-forth conversation

### Configuration Options:

```javascript
// Adjust these parameters for your needs:
this.vadThreshold = 0.01; // Voice detection sensitivity
this.silenceThreshold = 1500; // ms of silence before processing
this.volumeThreshold = 0.005; // Minimum volume for speech
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
