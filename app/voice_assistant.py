"""
Voice Assistant functionality for TaskFlow AI.
Integrates Google Speech-to-Text, Text-to-Speech, and existing LangChain pipeline.
"""

import json
import base64
import time
import signal
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from google.cloud import speech, texttospeech
from app import models
from app.llm_service import create_graph
from app.database import get_db
from app.config import settings


class VoiceAssistantService:
    """Service for handling voice-related operations."""
    
    def __init__(self, speech_client=None, tts_client=None):
        """Initialize voice assistant service."""
        self.speech_client = speech_client or self._initialize_speech_client()
        self.tts_client = tts_client or self._initialize_tts_client()
        
        # Audio processing optimization
        self.audio_buffer = bytearray()
        self.cached_encoding = None
        self.cached_sample_rate = None
        self.last_audio_time = 0
        self.silence_threshold = 2.0  # seconds
        self.min_audio_length = 1000  # minimum bytes for processing
        
        print("VoiceAssistantService initialized")
        print(f"Speech client available: {self.speech_client is not None}")
        print(f"TTS client available: {self.tts_client is not None}")
    
    def _initialize_speech_client(self):
        """Initialize Google Cloud Speech client."""
        try:
            from google.cloud import speech
            import os
            import json
            import tempfile
            
            # Check if credentials are available
            creds_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
            if not creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                print("No Google Cloud credentials found - speech recognition will not work")
                return None
            
            print("Initializing Google Cloud Speech client...")
            
            # If credentials JSON is provided as string (Railway environment)
            if creds_json:
                try:
                    # Parse and validate JSON
                    creds_data = json.loads(creds_json)
                    
                    # Create temporary file with credentials
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(creds_data, f)
                        temp_creds_path = f.name
                    
                    # Set environment variable for Google Cloud client
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                    print(f"Set Google Cloud credentials from JSON environment variable")
                    
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON in GOOGLE_CLOUD_CREDENTIALS_JSON: {e}")
                    return None
            
            # Initialize client
            client = speech.SpeechClient()
            
            # Test the client with a simple configuration
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
            )
            print("Speech client initialized successfully")
            return client
            
        except Exception as e:
            print(f"Failed to initialize Speech client: {e}")
            return None
    
    def _initialize_tts_client(self):
        """Initialize Google Cloud Text-to-Speech client."""
        try:
            from google.cloud import texttospeech
            import os
            import json
            import tempfile
            
            # Check if credentials are available
            creds_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
            if not creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                print("No Google Cloud credentials found - text-to-speech will not work")
                return None
                
            print("Initializing Google Cloud TTS client...")
            
            # If credentials JSON is provided as string (Railway environment)
            if creds_json:
                try:
                    # Parse and validate JSON
                    creds_data = json.loads(creds_json)
                    
                    # Create temporary file with credentials
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(creds_data, f)
                        temp_creds_path = f.name
                    
                    # Set environment variable for Google Cloud client
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                    print(f"Set Google Cloud credentials from JSON environment variable")
                    
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON in GOOGLE_CLOUD_CREDENTIALS_JSON: {e}")
                    return None
            
            # Initialize client
            client = texttospeech.TextToSpeechClient()
            
            # Test the client by creating a simple voice config
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US", name="en-US-Wavenet-D"
            )
            print("TTS client initialized successfully")
            return client
            
        except Exception as e:
            print(f"Failed to initialize TTS client: {e}")
            return None
    
    def get_speech_config(self, encoding=None, sample_rate=None):
        """Get speech recognition configuration."""
        return speech.RecognitionConfig(
            encoding=encoding or speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate or 16000,
            language_code=settings.SPEECH_LANGUAGE,
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            model="latest_long"
        )

    def try_speech_recognition(self, audio_data: bytes, use_cache: bool = True) -> Dict[str, Any]:
        """Try speech recognition with different audio encodings and sample rates."""
        print(f"🎤 Starting speech recognition: {len(audio_data)} bytes, use_cache={use_cache}")
        
        # If we have cached encoding, try it first
        if use_cache and self.cached_encoding and self.cached_sample_rate:
            try:
                print(f"Trying cached encoding: {self.cached_encoding} with sample rate: {self.cached_sample_rate}")
                config = self.get_speech_config(self.cached_encoding, self.cached_sample_rate)
                audio = speech.RecognitionAudio(content=audio_data)
                
                response = self.speech_client.recognize(config=config, audio=audio)
                
                if response.results and response.results[0].alternatives:
                    result = response.results[0]
                    transcript = result.alternatives[0].transcript.strip()
                    confidence = result.alternatives[0].confidence
                    
                    if transcript:
                        print(f"Success with cached encoding - Transcript: '{transcript}', Confidence: {confidence}")
                        return {
                            "transcript": transcript,
                            "confidence": confidence,
                            "success": True,
                            "encoding_used": str(self.cached_encoding),
                            "sample_rate_used": self.cached_sample_rate
                        }
                        
            except Exception as e:
                print(f"Cached encoding failed: {str(e)}")
                # Clear cache if it fails
                self.cached_encoding = None
                self.cached_sample_rate = None
        
        # Try different combinations if cache failed or not available
        encodings_to_try = [
            speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            speech.RecognitionConfig.AudioEncoding.LINEAR16,
            speech.RecognitionConfig.AudioEncoding.MULAW,
            speech.RecognitionConfig.AudioEncoding.FLAC,
        ]
        
        sample_rates_to_try = [16000, 48000, 44100, 8000]
        
        for encoding in encodings_to_try:
            for sample_rate in sample_rates_to_try:
                try:
                    print(f"Trying encoding: {encoding} with sample rate: {sample_rate}")
                    config = self.get_speech_config(encoding, sample_rate)
                    audio = speech.RecognitionAudio(content=audio_data)
                    
                    response = self.speech_client.recognize(config=config, audio=audio)
                    print(f"Speech recognition response for {encoding}@{sample_rate}: {response}")
                    
                    if response.results and response.results[0].alternatives:
                        result = response.results[0]
                        transcript = result.alternatives[0].transcript.strip()
                        confidence = result.alternatives[0].confidence
                        
                        print(f"Success with {encoding}@{sample_rate} - Transcript: '{transcript}', Confidence: {confidence}")
                        
                        if transcript:
                            # Cache the successful combination
                            self.cached_encoding = encoding
                            self.cached_sample_rate = sample_rate
                            print(f"Cached successful encoding: {encoding}@{sample_rate}")
                            
                            return {
                                "transcript": transcript,
                                "confidence": confidence,
                                "success": True,
                                "encoding_used": str(encoding),
                                "sample_rate_used": sample_rate
                            }
                            
                except Exception as e:
                    print(f"Failed with encoding {encoding}@{sample_rate}: {str(e)}")
                    continue
        
        return {"error": "No speech detected with any encoding/sample rate combination", "transcript": ""}

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
    
    def text_to_speech_fast(self, text: str) -> bytes:
        """Convert text to speech audio with faster, more responsive settings for continuous mode."""
        if self.tts_client is None:
            print("TTS client not available")
            return b""
        
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Standard-D"  # Standard voice for faster processing
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=1.2,  # Slightly faster speaking rate
                pitch=0.0,
                volume_gain_db=0.0
            )
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return response.audio_content
        except Exception as e:
            print(f"Fast TTS Error: {e}")
            # Fallback to regular TTS
            return self.text_to_speech(text)

    def add_audio_chunk(self, audio_data: bytes) -> bool:
        """Add audio chunk to buffer and return True if ready for processing."""
        self.audio_buffer.extend(audio_data)
        self.last_audio_time = time.time()
        
        print(f"Added audio chunk: {len(audio_data)} bytes, total buffer: {len(self.audio_buffer)} bytes")
        
        # Don't process until we have enough audio data
        return len(self.audio_buffer) >= self.min_audio_length

    def should_process_audio(self) -> bool:
        """Check if audio should be processed based on silence threshold."""
        current_time = time.time()
        time_since_last_audio = current_time - self.last_audio_time
        
        # Process if we have enough audio and it's been silent for the threshold
        return (len(self.audio_buffer) >= self.min_audio_length and 
                time_since_last_audio >= self.silence_threshold)

    def process_accumulated_audio(self) -> Dict[str, Any]:
        """Process the accumulated audio buffer."""
        if not self.audio_buffer:
            return {"error": "No audio data to process"}
        
        try:
            print(f"Processing accumulated audio: {len(self.audio_buffer)} bytes")
            
            # Process the accumulated audio
            audio_data = bytes(self.audio_buffer)
            result = self.try_speech_recognition(audio_data)
            
            # Clear the buffer after processing
            self.audio_buffer.clear()
            
            return result
            
        except Exception as e:
            print(f"Error processing accumulated audio: {str(e)}")
            self.audio_buffer.clear()
            return {"error": f"Audio processing failed: {str(e)}"}

    def process_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """Process audio chunk with buffering and caching."""
        if self.speech_client is None:
            return {"error": "Speech client not initialized - Google Cloud credentials may be missing"}
        
        try:
            # Add timeout to prevent hanging
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Speech processing timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                # Validate audio data
                if len(audio_data) < 100:
                    return {"error": "Audio data too short"}
                
                # Add to buffer
                ready_for_processing = self.add_audio_chunk(audio_data)
                
                # Only process if we have enough audio or it's been silent
                if ready_for_processing and self.should_process_audio():
                    return self.process_accumulated_audio()
                else:
                    # Return interim result indicating we're still collecting
                    return {"interim": True, "message": "Collecting audio..."}
                
            except Exception as e:
                print(f"Speech recognition error: {str(e)}")
                return {"error": f"Speech recognition failed: {str(e)}"}
            finally:
                signal.alarm(0)
                
        except TimeoutError:
            return {"error": "Speech processing timed out"}
        except Exception as e:
            print(f"Audio processing error: {str(e)}")
            return {"error": f"Audio processing failed: {str(e)}"}

    def force_process_audio(self) -> Dict[str, Any]:
        """Force process accumulated audio (for end of recording)."""
        if not self.audio_buffer:
            return {"error": "No audio data to process"}
        
        return self.process_accumulated_audio()

    def clear_audio_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()
        print("Audio buffer cleared")
    
    def process_audio_immediate(self, audio_data: bytes) -> Dict[str, Any]:
        """Process audio immediately without buffering for continuous mode."""
        print(f"🎯 Processing audio immediately: {len(audio_data)} bytes")
        
        if self.speech_client is None:
            print("❌ Speech client not initialized")
            return {"error": "Speech client not initialized - Google Cloud credentials may be missing"}
        
        try:
            # Validate audio data
            if len(audio_data) < 100:
                print(f"❌ Audio data too short: {len(audio_data)} bytes")
                return {"error": "Audio data too short"}
            
            # Process immediately with shorter timeout for real-time response
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Speech processing timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # Shorter timeout for continuous mode
            
            try:
                result = self.try_speech_recognition(audio_data, use_cache=False)
                return result
                
            except Exception as e:
                print(f"Immediate speech recognition error: {str(e)}")
                return {"error": f"Speech recognition failed: {str(e)}"}
            finally:
                signal.alarm(0)
                
        except TimeoutError:
            return {"error": "Speech processing timed out"}
        except Exception as e:
            print(f"Immediate audio processing error: {str(e)}")
            return {"error": f"Audio processing failed: {str(e)}"}

    def process_with_langchain(self, transcript: str, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
        """Process transcript with existing LangChain pipeline."""
        try:
            if team_names is None:
                team_names = []
            
            # Add timeout to prevent hanging
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LangChain processing timed out")
            
            # Set a 30-second timeout for LangChain processing
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            try:
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
            finally:
                # Clear the alarm
                signal.alarm(0)
            
        except TimeoutError:
            return {"error": "Task processing timed out - please try again with a simpler request", "is_complete": False}
        except Exception as e:
            return {"error": f"Task processing failed: {str(e)}", "is_complete": False}


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
        """Process audio stream from WebSocket."""
        session_name = "Default"
        team_names = []
        full_transcript = ""
        is_continuous_mode = False

        try:
            while True:
                message = await websocket.receive_text()
                
                try:
                    data = json.loads(message)

                    # Handle actions like interruption or session updates
                    if "action" in data:
                        if data["action"] == "interrupt":
                            print("Received interrupt action")
                            self.service.clear_audio_buffer()
                            full_transcript = ""  # Reset transcript on interrupt
                            await websocket.send_json({"status": "interrupted", "message": "Assistant interrupted."})
                        continue

                    if "session_name" in data:
                        session_name = data["session_name"]
                        await websocket.send_json({"status": "session_updated", "session_name": session_name})
                        continue

                    # Get audio data and continuous mode flag
                    audio_data_b64 = data.get("audio")
                    is_continuous_mode = data.get("continuous_mode", False)

                    print(f"🎵 Received audio message: audio_length={len(audio_data_b64) if audio_data_b64 else 0}, continuous_mode={is_continuous_mode}")

                    if not audio_data_b64:
                        print("❌ No audio data provided in message")
                        await websocket.send_json({"error": "No audio data provided"})
                        continue
                        
                    audio_data = base64.b64decode(audio_data_b64)
                    print(f"🔊 Decoded audio data: {len(audio_data)} bytes")

                    if is_continuous_mode:
                        # Process audio immediately in continuous mode
                        result = self.service.process_audio_immediate(audio_data)
                        
                        if "transcript" in result and result["transcript"]:
                            full_transcript += " " + result["transcript"]
                            await self._process_transcript(
                                websocket,
                                full_transcript.strip(),
                                user_id,
                                session_name,
                                team_names,
                                continuous_mode=True
                            )
                        elif "error" in result:
                            await websocket.send_json({"error": result["error"]})

                    else:
                        # Buffer audio in regular mode
                        self.service.add_audio_chunk(audio_data)
                        if self.service.should_process_audio():
                            transcript_data = self.service.process_accumulated_audio()
                            
                            if "transcript" in transcript_data and transcript_data["transcript"]:
                                full_transcript = transcript_data["transcript"]
                                await self._process_transcript(
                                    websocket,
                                    full_transcript,
                                    user_id,
                                    session_name,
                                    team_names,
                                    continuous_mode=False
                                )
                                self.service.clear_audio_buffer()
                            elif "error" in transcript_data:
                                await websocket.send_json({"error": transcript_data["error"]})
                                self.service.clear_audio_buffer()

                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue
        
        except WebSocketDisconnect:
            print("WebSocket disconnected.")
            if full_transcript and not is_continuous_mode:
                # Process any remaining transcript in non-continuous mode
                await self._process_transcript(websocket, full_transcript, user_id, session_name, team_names, False)
        
        except Exception as e:
            # Catch any other exceptions and send an error message
            error_message = f"An unexpected error occurred: {str(e)}"
            print(error_message)
            try:
                await websocket.send_json({"error": error_message})
            except Exception as send_error:
                print(f"Failed to send error message to client: {send_error}")

        finally:
            print("Closing WebSocket connection.")
            # Only close if not already closed
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
    
    async def _process_transcript(self, websocket: WebSocket, transcript: str, user_id: int, session_name: str, team_names: list, continuous_mode: bool = False):
        """Process transcript with LangChain and send response."""
        try:
            # Process with LangChain using proper user context
            llm_result = self.service.process_with_langchain(
                transcript, 
                user_id=user_id,
                session_name=session_name,
                team_names=team_names
            )
            
            # Handle LangChain processing errors
            if "error" in llm_result:
                error_msg = llm_result["error"]
                if "timeout" in error_msg.lower():
                    response_text = "Task creation timed out. Please try again with a simpler request."
                else:
                    response_text = f"Task creation failed: {error_msg}"
                
                await websocket.send_json({
                    "error": response_text,
                    "response_text": response_text,
                    "transcript": transcript,
                    "continuous_mode": continuous_mode
                })
                return
            
            # Generate response message
            if llm_result.get("is_complete"):
                response_text = f"Task '{llm_result.get('task_title', 'created')}' has been created successfully!"
            else:
                clarification_questions = llm_result.get("clarification_questions", [])
                if clarification_questions:
                    response_text = clarification_questions[0]
                else:
                    response_text = "I need more information to create the task."
            
            # Convert to speech (with error handling)
            audio_response = None
            try:
                if continuous_mode:
                    # Generate faster, shorter audio for continuous mode
                    audio_response = self.service.text_to_speech_fast(response_text)
                else:
                    audio_response = self.service.text_to_speech(response_text)
            except Exception as e:
                print(f"Text-to-speech error: {e}")
                # Continue without audio response
            
            # Send response
            await websocket.send_json({
                "transcript": transcript,
                "response": base64.b64encode(audio_response).decode() if audio_response else "",
                "response_text": response_text,
                "llm_result": llm_result,
                "continuous_mode": continuous_mode
            })
            
        except Exception as e:
            print(f"Error processing transcript: {e}")
            await websocket.send_json({
                "error": f"Processing error: {str(e)}",
                "response_text": "Sorry, I encountered an error processing your request.",
                "continuous_mode": continuous_mode
            })
    
    def process_voice_command(self, audio_data: bytes, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
        """Process a single voice command (non-streaming)."""
        try:
            # Step 1: Speech-to-Text
            result = self.service.process_audio_chunk(audio_data)

            if "error" in result:
                return result

            transcript = result.get("transcript", "")
            if not transcript:
                return {"error": "No transcript found", "task_created": False}
            
            # Step 2: Process with LangChain
            if team_names is None:
                team_names = []
            
            llm_result = self.service.process_with_langchain(transcript, user_id, session_name, team_names)

            # Combine results
            result.update(llm_result)

            # Step 3: Text-to-Speech
            response_text = result.get("response", "")
            if response_text:
                audio_response = self.service.text_to_speech(response_text)
                result["audio_response"] = base64.b64encode(audio_response).decode("utf-8")
            
            return result

        except Exception as e:
            return {"error": str(e), "task_created": False}


# Helper function for tests
def get_langchain_response(transcript: str, user_id: int, session_name: str, team_names: list = None) -> Dict[str, Any]:
    """Helper function to get LangChain response (for testing purposes)."""
    if team_names is None:
        team_names = []
    service = VoiceAssistantService()
    return service.process_with_langchain(transcript, user_id, session_name, team_names) 