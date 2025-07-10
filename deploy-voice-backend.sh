#!/bin/bash

# 🎤 Voice Assistant Backend Deployment Script
# This script helps deploy the voice assistant backend to Railway

set -e

echo "🚀 Voice Assistant Backend Deployment"
echo "======================================"

# Check if backend directory exists
if [ ! -d "../to_do_list" ]; then
    echo "❌ Backend directory not found at ../to_do_list"
    echo "Please ensure the backend is in the correct location"
    exit 1
fi

# Check if voice_assistant.py exists
if [ ! -f "../to_do_list/app/voice_assistant.py" ]; then
    echo "❌ voice_assistant.py not found in backend"
    echo "Please ensure the voice assistant backend is implemented"
    exit 1
fi

echo "✅ Backend files found"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    echo "Please install Railway CLI: npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI found"

# Change to backend directory
cd ../to_do_list

# Check if it's a Railway project
if [ ! -f "railway.toml" ]; then
    echo "❌ Not a Railway project"
    echo "Please run 'railway init' in the backend directory first"
    exit 1
fi

echo "✅ Railway project detected"

# Check environment variables
echo "🔧 Checking environment variables..."

# Check if Google Cloud credentials are set
if ! railway variables get GOOGLE_CLOUD_CREDENTIALS_JSON &> /dev/null; then
    echo "⚠️ GOOGLE_CLOUD_CREDENTIALS_JSON not set"
    echo "Please set Google Cloud credentials in Railway dashboard"
    echo "Railway dashboard: https://railway.app/project/your-project/variables"
fi

if ! railway variables get GOOGLE_CLOUD_PROJECT &> /dev/null; then
    echo "⚠️ GOOGLE_CLOUD_PROJECT not set"
    echo "Please set Google Cloud project ID in Railway dashboard"
fi

# Check if required dependencies are in requirements.txt
echo "🔧 Checking dependencies..."

if ! grep -q "google-cloud-speech" requirements.txt; then
    echo "⚠️ Adding google-cloud-speech to requirements.txt"
    echo "google-cloud-speech" >> requirements.txt
fi

if ! grep -q "google-cloud-texttospeech" requirements.txt; then
    echo "⚠️ Adding google-cloud-texttospeech to requirements.txt"
    echo "google-cloud-texttospeech" >> requirements.txt
fi

if ! grep -q "websockets" requirements.txt; then
    echo "⚠️ Adding websockets to requirements.txt"
    echo "websockets" >> requirements.txt
fi

echo "✅ Dependencies checked"

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo ""
echo "🎉 Next Steps:"
echo "1. Check Railway dashboard for deployment status"
echo "2. Test WebSocket connection: wss://your-app.up.railway.app/ws/voice"
echo "3. Try the voice assistant in your frontend"
echo ""
echo "🔧 If you encounter issues:"
echo "1. Check Railway logs: railway logs"
echo "2. Verify environment variables in Railway dashboard"
echo "3. Test Google Cloud credentials"
echo ""
echo "📚 Documentation: See VOICE_ASSISTANT_DEPLOYMENT.md for full guide" 