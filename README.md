# 🎯 TaskFlow AI - Intelligent Task Management

> **Modern task management with AI-powered features and voice assistance**

## 🚀 Features

### Core Task Management

- ✅ **Create, Read, Update, Delete** tasks with full CRUD operations
- 📅 **Time Management** - Schedule tasks with dates and times
- 👥 **Team Collaboration** - Create sessions and invite team members
- 🔐 **User Authentication** - Secure JWT-based authentication
- 📱 **Privacy Controls** - Private, team, and global public tasks

### 🎤 NEW: Voice Assistant (LangSmith Integrated)

- **🎙️ Voice-to-Task**: Create tasks using natural speech
- **🧠 AI Processing**: Powered by LangGraph and OpenAI GPT-4
- **📊 Real-time Monitoring**: LangSmith integration for tracing
- **🔐 Secure**: JWT-authenticated WebSocket connections
- **👥 Context-Aware**: Understands team and session context

### 🤖 AI-Powered Features

- **💬 Chat Interface**: Conversational task creation
- **🧠 Intelligent Parsing**: Natural language understanding
- **📊 LangSmith Tracing**: Monitor AI operations in real-time
- **⚡ Real-time Processing**: Instant task creation and updates

## 📋 Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd to_do_list

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file:

```env
DATABASE_URL=sqlite:///./taskflow.db
OPENAI_API_KEY=sk-your-openai-api-key-here
LANGCHAIN_API_KEY=lsv2_your-langsmith-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=TaskFlow-TodoList
SECRET_KEY=your-secret-key-here
```

### 3. Start Application

```bash
uvicorn app.main:app --reload
```

### 4. Access Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Voice Assistant**: `ws://localhost:8000/ws/voice?token=JWT_TOKEN`

## 🎤 Voice Assistant Setup

### Quick Start (5 minutes)

👉 **See [VOICE_QUICKSTART.md](VOICE_QUICKSTART.md)** for rapid setup

### Complete Guide

👉 **See [VOICE_FEATURE_README.md](VOICE_FEATURE_README.md)** for comprehensive documentation

### Voice Commands Examples

```
"Create a task to call John at 3 PM"
"Remind me to buy groceries tomorrow"
"Schedule a team meeting next week"
"Add a task to finish the report by Friday"
```

## 🔧 API Endpoints

### Authentication

```
POST /token                    # Get JWT token
POST /users/                   # Create user account
POST /auth/register            # Register with email verification
```

### Tasks

```
GET    /todos/                 # Get all tasks
POST   /todos/                 # Create new task
GET    /todos/{id}             # Get specific task
PUT    /todos/{id}             # Update task
DELETE /todos/{id}             # Delete task
```

### Time Management

```
GET /todos/today               # Today's tasks
GET /todos/week                # This week's tasks
GET /todos/month               # This month's tasks
GET /todos/overdue             # Overdue tasks
GET /todos/range               # Tasks in date range
```

### Team Management

```
GET    /sessions/              # Get user sessions
POST   /sessions/              # Create team session
POST   /sessions/{id}/invite   # Invite user to session
GET    /sessions/{id}/todos    # Get session tasks
GET    /sessions/{id}/members  # Get session members
```

### AI Features

```
POST /chat/create-task         # Conversational task creation
WS   /ws/voice                 # Voice assistant WebSocket
```

## 🧪 Testing

### Run All Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Voice assistant tests
python run_voice_assistant_tests.py

# Comprehensive tests with coverage
python run_comprehensive_voice_tests.py
```

### Test Categories

- **Unit Tests**: Core functionality testing
- **Integration Tests**: API endpoint testing
- **Voice Tests**: Voice assistant functionality
- **Smoke Tests**: Production readiness checks
- **UI Tests**: Frontend integration testing

## 📊 LangSmith Monitoring

### Real-time Tracing

1. Open [LangSmith Dashboard](https://smith.langchain.com/)
2. Navigate to your project
3. Monitor:
   - Voice transcription processing
   - LangGraph task parsing
   - Database operations
   - Response generation

### Key Metrics

- **Latency**: Response time for voice commands
- **Success Rate**: Percentage of successful task creations
- **Error Rate**: Failed processing attempts
- **Token Usage**: OpenAI API consumption

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React/HTML)  │◄──►│   (FastAPI)     │◄──►│   (SQLite/      │
│                 │    │                 │    │    PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   Voice         │              │
         └─────────────►│   Assistant     │◄─────────────┘
                        │   (WebSocket)   │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │   AI Services   │
                        │                 │
                        │  ┌──────────┐   │
                        │  │ LangGraph│   │
                        │  └──────────┘   │
                        │  ┌──────────┐   │
                        │  │ OpenAI   │   │
                        │  └──────────┘   │
                        │  ┌──────────┐   │
                        │  │LangSmith │   │
                        │  └──────────┘   │
                        └─────────────────┘
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for password security
- **User Isolation**: Tasks are user-scoped
- **Session Management**: Team-based access control
- **Input Validation**: Comprehensive input sanitization
- **CORS Protection**: Cross-origin request security

## 🚀 Production Deployment

### Database Configuration

For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:port/database
```

### Environment Variables

```env
# Production settings
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=lsv2_...
SECRET_KEY=strong-production-secret
```

### Deployment Options

- **Railway**: Easy deployment with database
- **Heroku**: Container-based deployment
- **AWS**: EC2 + RDS setup
- **Docker**: Containerized deployment

## 📚 Documentation

- **[VOICE_FEATURE_README.md](VOICE_FEATURE_README.md)** - Complete voice assistant guide
- **[VOICE_QUICKSTART.md](VOICE_QUICKSTART.md)** - 5-minute voice setup
- **[PRODUCTION_DATABASE_GUIDE.md](PRODUCTION_DATABASE_GUIDE.md)** - Production database setup
- **[VOICE_ASSISTANT_DEVELOPMENT_GUIDE.md](VOICE_ASSISTANT_DEVELOPMENT_GUIDE.md)** - Development guide
- **[COMPREHENSIVE_TDD_IMPLEMENTATION_SUMMARY.md](COMPREHENSIVE_TDD_IMPLEMENTATION_SUMMARY.md)** - Testing overview

## 🛠️ Development

### Project Structure

```
to_do_list/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── crud.py              # Database operations
│   ├── schemas.py           # Pydantic schemas
│   ├── voice_assistant.py   # Voice processing
│   ├── llm_service.py       # LangGraph integration
│   └── config.py            # Configuration
├── tests/                   # Test suites
├── alembic/                 # Database migrations
└── requirements.txt         # Dependencies
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit pull request

## 🎯 Roadmap

### Upcoming Features

- [ ] Mobile app support
- [ ] Voice assistant improvements
- [ ] Advanced AI features
- [ ] Better team collaboration
- [ ] Task templates
- [ ] Calendar integration
- [ ] Notification system

### Voice Assistant Enhancements

- [ ] Multiple language support
- [ ] Voice customization
- [ ] Offline capabilities
- [ ] Advanced conversation handling
- [ ] Voice shortcuts

## 📞 Support

### Getting Help

1. Check the documentation links above
2. Review LangSmith traces for AI-related issues
3. Check server logs for debugging
4. Review test results for functionality issues

### Common Issues

- **Database Connection**: Check `DATABASE_URL` in `.env`
- **Authentication**: Verify JWT token validity
- **Voice Assistant**: Ensure API keys are set correctly
- **LangSmith**: Check project name and API key

## 🏆 Features Highlights

### ✨ What Makes TaskFlow Special

- **🎤 Voice-First**: Create tasks naturally with speech
- **🧠 AI-Powered**: Intelligent task parsing and processing
- **📊 Observable**: Real-time monitoring with LangSmith
- **👥 Collaborative**: Team-based task management
- **🔐 Secure**: Enterprise-grade authentication
- **⚡ Fast**: Real-time WebSocket communication
- **🧪 Tested**: >90% test coverage with TDD approach

---

**🎤 Ready to revolutionize your task management? Start with voice commands today!**

_Built with ❤️ using FastAPI, LangChain, and modern AI technologies_
