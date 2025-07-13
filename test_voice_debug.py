#!/usr/bin/env python3
"""
Debug script to test voice assistant processing locally.
"""

import asyncio
import json
import base64
import websockets
from app.voice_assistant import VoiceAssistantService

async def test_voice_processing():
    """Test voice processing with a simple audio file."""
    print("🧪 Testing voice assistant processing...")
    
    # Initialize the voice assistant service
    service = VoiceAssistantService()
    
    # Create a simple test audio (base64 encoded silence)
    test_audio = b'\x00' * 1000  # 1000 bytes of silence
    
    print(f"📊 Testing with {len(test_audio)} bytes of audio data")
    
    # Test speech recognition
    result = service.try_speech_recognition(test_audio)
    print(f"🎯 Speech recognition result: {result}")
    
    # Test with LangChain if we get a transcript
    if result.get('transcript'):
        print(f"📝 Processing transcript: '{result['transcript']}'")
        llm_result = service.process_with_langchain(
            result['transcript'], 
            user_id=1,
            session_name="Test Session",
            team_names=[]
        )
        print(f"🤖 LangChain result: {llm_result}")
    else:
        print("❌ No transcript generated - testing with sample text")
        llm_result = service.process_with_langchain(
            "Create a task to test the voice assistant",
            user_id=1,
            session_name="Test Session", 
            team_names=[]
        )
        print(f"🤖 LangChain result: {llm_result}")

if __name__ == "__main__":
    asyncio.run(test_voice_processing()) 