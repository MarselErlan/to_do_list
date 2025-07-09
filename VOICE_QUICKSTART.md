# 🚀 Voice Assistant - Quick Start (5 Minutes)

## Prerequisites

- Python 3.11+
- OpenAI API key
- LangSmith account (optional but recommended)

## Quick Setup

### 1. Environment Setup (1 minute)

```bash
# Create .env file
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./taskflow.db
OPENAI_API_KEY=sk-your-openai-api-key-here
LANGCHAIN_API_KEY=lsv2_your-langsmith-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=TaskFlow-Voice-Assistant
SECRET_KEY=your-secret-key-here
EOF
```

### 2. Start Server (1 minute)

```bash
# Install dependencies (if needed)
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload
```

### 3. Create User & Get Token (1 minute)

```bash
# Create user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# Get JWT token
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"
```

### 4. Test Voice Connection (2 minutes)

Save this as `test_voice.html`:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Voice Test</title>
  </head>
  <body>
    <h1>🎤 Voice Assistant Test</h1>
    <button id="test">Test Connection</button>
    <div id="result"></div>

    <script>
      const token = "YOUR_JWT_TOKEN_HERE"; // Replace with actual token

      document.getElementById("test").onclick = () => {
        const ws = new WebSocket(`ws://localhost:8000/ws/voice?token=${token}`);

        ws.onopen = () => {
          document.getElementById("result").innerHTML = "✅ Connected!";

          // Test with dummy audio
          ws.send(
            JSON.stringify({
              audio: "ZHVtbXlfYXVkaW9fZGF0YQ==", // dummy base64
            })
          );
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          document.getElementById(
            "result"
          ).innerHTML += `<br>📨 Response: ${JSON.stringify(data, null, 2)}`;
        };

        ws.onerror = (error) => {
          document.getElementById("result").innerHTML = `❌ Error: ${error}`;
        };
      };
    </script>
  </body>
</html>
```

### 5. Monitor in LangSmith

1. Open [LangSmith Dashboard](https://smith.langchain.com/)
2. Navigate to your project: `TaskFlow-Voice-Assistant`
3. Watch real-time traces! 🎉

## Voice Commands to Try

- "Hello" → Get greeting
- "Create a task to call John tomorrow at 3 PM" → Create task
- "Remind me to buy groceries" → Create reminder
- "Schedule a team meeting next week" → Team task

## Common Issues & Fixes

### Database Error

```bash
# If you see SQLAlchemy URL error:
export DATABASE_URL=sqlite:///./taskflow.db
```

### Authentication Error

```bash
# If WebSocket fails, check token in URL:
ws://localhost:8000/ws/voice?token=YOUR_ACTUAL_TOKEN
```

### No LangSmith Traces

- Check `LANGCHAIN_API_KEY` is correct
- Verify project name matches in dashboard

## That's It! 🎉

Your voice assistant is now ready for task creation with LangSmith monitoring!
