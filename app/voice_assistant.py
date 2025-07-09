"""
Voice Assistant functionality for TaskFlow AI.
Integrates Google Speech-to-Text, Text-to-Speech, and existing LangChain pipeline.
"""

import json
import base64
import asyncio
import tempfile
import os
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from google.cloud import speech, texttospeech
from app.llm_service import create_graph
from app.database import get_db
from app.models import User, Session
from app.config import settings


class VoiceAssistantService:
    """Service class for handling voice processing operations."""
    
    def __init__(self, speech_client=None, tts_client=None):
        """Initialize voice assistant service with optional Google Cloud clients for testing."""
        self.rate = 16000
        self.chunk_size = 1600  # 100ms chunks
        
        # Allow client injection for testing
        if speech_client is not None:
            self.speech_client = speech_client
        else:
            self.speech_client = self._initialize_speech_client()
        
        if tts_client is not None:
            self.tts_client = tts_client
        else:
            self.tts_client = self._initialize_tts_client()
    
    def _initialize_speech_client(self):
        """Initialize Google Cloud Speech client with proper credential handling."""
        try:
            # If credentials JSON is provided as string (for Railway deployment)
            if settings.GOOGLE_CLOUD_CREDENTIALS_JSON:
                # Create temporary file with credentials
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(settings.GOOGLE_CLOUD_CREDENTIALS_JSON)
                    temp_creds_path = f.name
                
                # Set environment variable for Google Cloud client
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                return speech.SpeechClient()
            
            # If credentials file path is provided
            elif settings.GOOGLE_APPLICATION_CREDENTIALS:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
                return speech.SpeechClient()
            
            # Try default credentials
            else:
                return speech.SpeechClient()
                
        except Exception as e:
            print(f"Warning: Could not initialize speech client: {e}")
            return None
    
    def _initialize_tts_client(self):
        """Initialize Google Cloud Text-to-Speech client with proper credential handling."""
        try:
            # If credentials JSON is provided as string (for Railway deployment)
            if settings.GOOGLE_CLOUD_CREDENTIALS_JSON:
                # Create temporary file with credentials
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(settings.GOOGLE_CLOUD_CREDENTIALS_JSON)
                    temp_creds_path = f.name
                
                # Set environment variable for Google Cloud client
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                return texttospeech.TextToSpeechClient()
            
            # If credentials file path is provided
            elif settings.GOOGLE_APPLICATION_CREDENTIALS:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
                return texttospeech.TextToSpeechClient()
            
            # Try default credentials
            else:
                return texttospeech.TextToSpeechClient()
                
        except Exception as e:
            print(f"Warning: Could not initialize TTS client: {e}")
            return None
    
    def get_speech_config(self) -> speech.RecognitionConfig:
        """Get speech recognition configuration."""
        if self.speech_client is None:
            raise RuntimeError("Speech client not initialized")
        
        return speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.rate,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
    
    def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech audio."""
        if self.tts_client is None:
            print("TTS client not available")
            return b""
        
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Wavenet-D"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.0
            )
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return response.audio_content
        except Exception as e:
            print(f"TTS Error: {e}")
            return b""
    
    def process_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """Process audio chunk and return transcription result."""
        if self.speech_client is None:
            return {"error": "Speech client not initialized"}
        
        try:
            config = self.get_speech_config()
            streaming_config = speech.StreamingRecognitionConfig(
                config=config, 
                interim_results=True
            )
            
            request = speech.StreamingRecognizeRequest(audio_content=audio_data)
            responses = self.speech_client.streaming_recognize(
                streaming_config, [request]
            )
            
            for response in responses:
                if not response.results:
                    continue
                result = response.results[0]
                if not result.alternatives:
                    continue
                
                transcript = result.alternatives[0].transcript
                return {
                    "transcript": transcript,
                    "is_final": result.is_final
                }
            
            return {"transcript": "", "is_final": False}
            
        except Exception as e:
            return {"error": str(e)}
    
    def process_with_langchain(self, transcript: str, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
        """Process transcript with existing LangChain pipeline."""
        try:
            if team_names is None:
                team_names = []
            
            # Use existing LangChain graph
            graph = create_graph()
            
            # Build state for LangChain processing
            state = {
                "user_query": transcript,
                "history": [{"sender": "user", "text": transcript}],
                "session_name": session_name,
                "team_names": team_names,
                "is_complete": False
            }
            
            # Create config for LangChain
            config = {
                "configurable": {
                    "db_session": next(get_db()),
                    "owner_id": user_id
                }
            }
            
            # Process with LangChain
            result = graph.invoke(state, config)
            
            return result
            
        except Exception as e:
            return {"error": str(e), "is_complete": False}


class VoiceAssistant:
    """Main voice assistant class handling WebSocket connections."""
    
    def __init__(self):
        """Initialize voice assistant."""
        self.service = VoiceAssistantService()
    
    async def websocket_endpoint(self, websocket: WebSocket, user_id: int):
        """Handle WebSocket connection for voice assistant."""
        await websocket.accept()
        await self.process_audio_stream(websocket, user_id)
    
    async def process_audio_stream(self, websocket: WebSocket, user_id: int):
        """Process continuous audio stream from WebSocket."""
        try:
            # Get user context from database
            db = next(get_db())
            try:
                # Get user's sessions/teams for context
                user_sessions = db.query(models.Session).join(models.SessionMember).filter(
                    models.SessionMember.user_id == user_id
                ).all()
                team_names = [session.name for session in user_sessions if session.name]
                
                # Default session context
                current_session_name = "Personal"
                
                while True:
                    # Receive audio data from client
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle session context updates
                    if "session_name" in message:
                        current_session_name = message["session_name"]
                        await websocket.send_json({"session_updated": current_session_name})
                        continue
                    
                    if "audio" in message:
                        audio_data = base64.b64decode(message["audio"])
                        
                        # Process audio chunk
                        result = self.service.process_audio_chunk(audio_data)
                        
                        if "error" in result:
                            await websocket.send_json({"error": result["error"]})
                            continue
                        
                        transcript = result.get("transcript", "")
                        is_final = result.get("is_final", False)
                        
                        if is_final and transcript:
                            # Process with LangChain using proper user context
                            llm_result = self.service.process_with_langchain(
                                transcript, 
                                user_id=user_id,
                                session_name=current_session_name,
                                team_names=team_names
                            )
                            
                            # Generate response message
                            if llm_result.get("is_complete"):
                                response_text = f"Task '{llm_result.get('task_title', 'created')}' has been created successfully!"
                            else:
                                clarification_questions = llm_result.get("clarification_questions", [])
                                if clarification_questions:
                                    response_text = clarification_questions[0]
                                else:
                                    response_text = "I need more information to create the task."
                            
                            # Convert to speech
                            audio_response = self.service.text_to_speech(response_text)
                            
                            # Send response
                            await websocket.send_json({
                                "transcript": transcript,
                                "response": base64.b64encode(audio_response).decode() if audio_response else "",
                                "response_text": response_text,
                                "llm_result": llm_result
                            })
                        else:
                            # Send interim result
                            await websocket.send_json({
                                "interim_transcript": transcript
                            })
                            
            finally:
                db.close()
                        
        except WebSocketDisconnect:
            pass
        except Exception as e:
            await websocket.send_json({"error": str(e)})
        finally:
            await websocket.close()
    
    def process_voice_command(self, audio_data: bytes, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
        """Process a single voice command (for testing/non-WebSocket use)."""
        if team_names is None:
            team_names = []
        
        # Process audio
        result = self.service.process_audio_chunk(audio_data)
        
        if "error" in result:
            return {"error": result["error"]}
        
        transcript = result.get("transcript", "")
        if not transcript:
            return {"error": "No speech detected"}
        
        # Process with LangChain
        llm_result = self.service.process_with_langchain(transcript, user_id, session_name, team_names)
        
        # Generate response
        if llm_result.get("is_complete"):
            response_text = f"Task '{llm_result.get('task_title', 'created')}' has been created successfully!"
            audio_response = self.service.text_to_speech(response_text)
            
            return {
                "task_created": True,
                "task_title": llm_result.get("task_title"),
                "transcript": transcript,
                "audio_response": base64.b64encode(audio_response).decode() if audio_response else "",
                "llm_result": llm_result
            }
        else:
            clarification_questions = llm_result.get("clarification_questions", [])
            response_text = clarification_questions[0] if clarification_questions else "I need more information to create the task."
            
            return {
                "task_created": False,
                "transcript": transcript,
                "clarification_needed": True,
                "response_text": response_text,
                "llm_result": llm_result
            }


# Helper function for tests
def get_langchain_response(transcript: str, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
    """Helper function to get LangChain response (for testing purposes)."""
    if team_names is None:
        team_names = []
    service = VoiceAssistantService()
    return service.process_with_langchain(transcript, user_id, session_name, team_names) 