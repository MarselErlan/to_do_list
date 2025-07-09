"""
Voice Assistant functionality for TaskFlow AI.
Integrates Google Speech-to-Text, Text-to-Speech, and existing LangChain pipeline.
"""

import json
import base64
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from google.cloud import speech, texttospeech
from app.llm_service import create_graph
from app.database import get_db
from app.models import User, Session


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
            try:
                self.speech_client = speech.SpeechClient()
            except Exception as e:
                print(f"Warning: Could not initialize speech client: {e}")
                self.speech_client = None
        
        if tts_client is not None:
            self.tts_client = tts_client
        else:
            try:
                self.tts_client = texttospeech.TextToSpeechClient()
            except Exception as e:
                print(f"Warning: Could not initialize TTS client: {e}")
                self.tts_client = None
    
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
    
    def process_with_langchain(self, transcript: str, user_id: int, session_name: str) -> Dict[str, Any]:
        """Process transcript with existing LangChain pipeline."""
        try:
            # Use existing LangChain graph
            graph = create_graph()
            
            # Build state for LangChain processing
            state = {
                "user_query": transcript,
                "history": [{"sender": "user", "text": transcript}],
                "session_name": session_name,
                "team_names": [],  # TODO: Get actual team names
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
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """Handle WebSocket connection for voice assistant."""
        await websocket.accept()
        await self.process_audio_stream(websocket)
    
    async def process_audio_stream(self, websocket: WebSocket):
        """Process continuous audio stream from WebSocket."""
        try:
            while True:
                # Receive audio data from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
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
                        # Process with LangChain
                        llm_result = self.service.process_with_langchain(
                            transcript, 
                            user_id=1,  # TODO: Get actual user ID
                            session_name="Personal"  # TODO: Get actual session
                        )
                        
                        # Generate response message
                        if llm_result.get("is_complete"):
                            response_text = f"Task '{llm_result.get('task_title', 'created')}' has been created successfully!"
                        else:
                            response_text = "I need more information to create the task."
                        
                        # Convert to speech
                        audio_response = self.service.text_to_speech(response_text)
                        
                        # Send response
                        await websocket.send_json({
                            "transcript": transcript,
                            "response": base64.b64encode(audio_response).decode(),
                            "llm_result": llm_result
                        })
                    else:
                        # Send interim result
                        await websocket.send_json({
                            "interim_transcript": transcript
                        })
                        
        except WebSocketDisconnect:
            pass
        except Exception as e:
            await websocket.send_json({"error": str(e)})
        finally:
            await websocket.close()
    
    def process_voice_command(self, audio_data: bytes, user_id: int, session_name: str) -> Dict[str, Any]:
        """Process a single voice command (for testing/non-WebSocket use)."""
        # Process audio
        result = self.service.process_audio_chunk(audio_data)
        
        if "error" in result:
            return {"error": result["error"]}
        
        transcript = result.get("transcript", "")
        if not transcript:
            return {"error": "No speech detected"}
        
        # Process with LangChain
        llm_result = self.service.process_with_langchain(transcript, user_id, session_name)
        
        # Generate response
        if llm_result.get("is_complete"):
            response_text = f"Task '{llm_result.get('task_title', 'created')}' has been created successfully!"
            audio_response = self.service.text_to_speech(response_text)
            
            return {
                "task_created": True,
                "task_title": llm_result.get("task_title"),
                "transcript": transcript,
                "audio_response": base64.b64encode(audio_response).decode(),
                "llm_result": llm_result
            }
        else:
            return {
                "task_created": False,
                "transcript": transcript,
                "clarification_needed": True,
                "llm_result": llm_result
            }


# Helper function for tests
def get_langchain_response(transcript: str, user_id: int, session_name: str) -> Dict[str, Any]:
    """Helper function to get LangChain response (for testing purposes)."""
    service = VoiceAssistantService()
    return service.process_with_langchain(transcript, user_id, session_name) 