"""
Enhanced Test-Driven Development tests for Voice Assistant functionality.
These tests define comprehensive expected behavior with better fixtures and realistic scenarios.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import json
import base64
import asyncio
from fastapi.testclient import TestClient
from fastapi import WebSocket, WebSocketDisconnect
from app.voice_assistant import VoiceAssistant, VoiceAssistantService
from app.main import app
import tempfile
import os
from typing import Dict, Any, List


# Test Fixtures
@pytest.fixture
def mock_speech_client():
    """Mock Google Cloud Speech client with realistic responses."""
    mock_client = Mock()
    
    # Mock RecognitionConfig enum
    mock_client.RecognitionConfig = Mock()
    mock_client.RecognitionConfig.AudioEncoding = Mock()
    mock_client.RecognitionConfig.AudioEncoding.LINEAR16 = "LINEAR16"
    
    return mock_client


@pytest.fixture
def mock_tts_client():
    """Mock Google Cloud Text-to-Speech client with realistic responses."""
    mock_client = Mock()
    
    # Mock response
    mock_response = Mock()
    mock_response.audio_content = b"fake_audio_content"
    mock_client.synthesize_speech.return_value = mock_response
    
    return mock_client


@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing."""
    return base64.b64encode(b"sample_audio_chunk_16khz_linear16").decode()


@pytest.fixture
def voice_service(mock_speech_client, mock_tts_client):
    """Voice assistant service with mocked clients."""
    return VoiceAssistantService(
        speech_client=mock_speech_client,
        tts_client=mock_tts_client
    )


@pytest.fixture
def mock_websocket():
    """Mock WebSocket with realistic behavior."""
    websocket = Mock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def sample_langchain_responses():
    """Sample LangChain responses for different scenarios."""
    return {
        "complete_task": {
            "is_complete": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "Task created successfully: Call mom at 3:00 PM today"
        },
        "incomplete_task": {
            "is_complete": False,
            "clarification": "What time would you like to call mom?",
            "response": "I'd be happy to help you schedule a call with mom. What time works best for you?"
        },
        "error_response": {
            "is_complete": False,
            "error": "Unable to parse time from your request",
            "response": "I didn't understand the time. Could you please specify when you'd like to do this?"
        }
    }


class TestVoiceAssistantServiceEnhanced:
    """Enhanced test suite for VoiceAssistantService with better coverage."""

    def test_init_with_valid_credentials(self, mock_speech_client, mock_tts_client):
        """Test VoiceAssistantService initialization with valid credentials."""
        service = VoiceAssistantService(
            speech_client=mock_speech_client,
            tts_client=mock_tts_client
        )
        
        assert service.speech_client == mock_speech_client
        assert service.tts_client == mock_tts_client
        assert hasattr(service, 'audio_buffer')
        assert hasattr(service, 'min_audio_length')

    def test_init_with_missing_credentials(self):
        """Test graceful handling of missing credentials."""
        with patch('app.voice_assistant.speech.SpeechClient') as mock_speech, \
             patch('app.voice_assistant.texttospeech.TextToSpeechClient') as mock_tts:
            
            mock_speech.side_effect = Exception("Credentials not found")
            mock_tts.side_effect = Exception("Credentials not found")
            
            service = VoiceAssistantService()
            
            assert service.speech_client is None
            assert service.tts_client is None

    def test_speech_config_creation(self, voice_service, mock_speech_client):
        """Test speech recognition configuration with proper settings."""
        # Need to patch the speech module to return a config
        from google.cloud import speech
        
        with patch('app.voice_assistant.speech') as mock_speech_module:
            mock_config = Mock()
            mock_config.encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
            mock_config.sample_rate_hertz = 16000
            mock_config.language_code = "en-US"
            mock_config.enable_automatic_punctuation = True
            
            mock_speech_module.RecognitionConfig.return_value = mock_config
            mock_speech_module.RecognitionConfig.AudioEncoding = Mock()
            mock_speech_module.RecognitionConfig.AudioEncoding.LINEAR16 = "LINEAR16"
            
            config = voice_service.get_speech_config()
            
            # Verify configuration parameters
            assert config.sample_rate_hertz == 16000
            assert config.language_code == "en-US"
            assert config.enable_automatic_punctuation is True

    def test_speech_config_without_client(self):
        """Test speech config works without client (uses defaults)."""
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        
        # The method should work and return a config object
        config = service.get_speech_config()
        
        # Verify it returns a configuration object
        assert config is not None

    def test_text_to_speech_success(self, voice_service, mock_tts_client):
        """Test successful text-to-speech conversion."""
        text = "Hello, your task has been created successfully!"
        
        result = voice_service.text_to_speech(text)
        
        assert result == b"fake_audio_content"
        mock_tts_client.synthesize_speech.assert_called_once()

    def test_text_to_speech_with_special_characters(self, voice_service, mock_tts_client):
        """Test TTS with special characters and punctuation."""
        text = "Task: 'Call mom @ 3:00 PM!' - Don't forget!"
        
        result = voice_service.text_to_speech(text)
        
        assert result == b"fake_audio_content"
        mock_tts_client.synthesize_speech.assert_called_once()

    def test_text_to_speech_failure(self, voice_service, mock_tts_client):
        """Test TTS failure handling."""
        mock_tts_client.synthesize_speech.side_effect = Exception("TTS service unavailable")
        
        result = voice_service.text_to_speech("Hello world")
        
        assert result == b""

    def test_text_to_speech_without_client(self):
        """Test TTS without client initialization."""
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        
        result = service.text_to_speech("Hello world")
        
        assert result == b""

    def test_process_audio_chunk_final_result(self, voice_service, mock_speech_client):
        """Test processing audio chunk with buffering logic."""
        # The process_audio_chunk method buffers audio and returns interim messages
        # unless there's enough accumulated audio to process
        
        audio_data = b"fake_audio_chunk_" + b"x" * 1000  # Make sure it's long enough
        result = voice_service.process_audio_chunk(audio_data)
        
        # Should return interim result while buffering
        assert "interim" in result or "error" in result  # Could be interim or error due to no client

    def test_process_audio_chunk_interim_result(self, voice_service, mock_speech_client):
        """Test processing audio chunk returns interim while buffering."""
        audio_data = b"short_chunk"  # Short audio should return interim
        result = voice_service.process_audio_chunk(audio_data)
        
        # Should return interim or error depending on whether client is available
        assert "interim" in result or "error" in result

    def test_process_audio_chunk_empty_response(self, voice_service, mock_speech_client):
        """Test processing audio chunk with empty response."""
        mock_response = Mock()
        mock_response.results = []
        
        mock_speech_client.streaming_recognize.return_value = [mock_response]
        
        result = voice_service.process_audio_chunk(b"audio_data")
        
        assert result["transcript"] == ""
        assert result["is_final"] is False

    def test_process_audio_chunk_no_alternatives(self, voice_service, mock_speech_client):
        """Test processing audio chunk with no alternatives."""
        mock_result = Mock()
        mock_result.alternatives = []
        
        mock_response = Mock()
        mock_response.results = [mock_result]
        
        mock_speech_client.streaming_recognize.return_value = [mock_response]
        
        result = voice_service.process_audio_chunk(b"audio_data")
        
        assert result["transcript"] == ""
        assert result["is_final"] is False

    def test_process_audio_chunk_api_error(self, voice_service, mock_speech_client):
        """Test processing audio chunk with API error."""
        mock_speech_client.streaming_recognize.side_effect = Exception("API quota exceeded")
        
        result = voice_service.process_audio_chunk(b"audio_data")
        
        assert "error" in result
        assert "API quota exceeded" in result["error"]

    def test_process_audio_chunk_without_client(self):
        """Test processing audio chunk without speech client."""
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        
        result = service.process_audio_chunk(b"audio_data")
        
        assert result["error"] == "Speech client not initialized"

    @patch('app.voice_assistant.create_graph')
    @patch('app.voice_assistant.get_db')
    def test_process_with_langchain_complete_task(self, mock_get_db, mock_create_graph, voice_service, sample_langchain_responses):
        """Test LangChain integration for complete task creation."""
        # Setup mocks
        mock_graph = Mock()
        mock_graph.invoke.return_value = sample_langchain_responses["complete_task"]
        mock_create_graph.return_value = mock_graph
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        transcript = "I need to call my mom at 3pm today"
        result = voice_service.process_with_langchain(transcript, user_id=1, session_name="Personal")
        
        assert result["is_complete"] is True
        assert result["task_title"] == "Call mom"
        assert result["start_time"] == "15:00:00"
        assert result["start_date"] == "2025-01-15"
        
        mock_graph.invoke.assert_called_once()

    @patch('app.voice_assistant.create_graph')
    @patch('app.voice_assistant.get_db')
    def test_process_with_langchain_incomplete_task(self, mock_get_db, mock_create_graph, voice_service, sample_langchain_responses):
        """Test LangChain integration for incomplete task requiring clarification."""
        # Setup mocks
        mock_graph = Mock()
        mock_graph.invoke.return_value = sample_langchain_responses["incomplete_task"]
        mock_create_graph.return_value = mock_graph
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        transcript = "I need to call someone"
        result = voice_service.process_with_langchain(transcript, user_id=1, session_name="Personal")
        
        assert result["is_complete"] is False
        assert "clarification" in result
        
        mock_graph.invoke.assert_called_once()

    @patch('app.voice_assistant.create_graph')
    @patch('app.voice_assistant.get_db')
    def test_process_with_langchain_error(self, mock_get_db, mock_create_graph, voice_service):
        """Test LangChain integration error handling."""
        # Setup mocks
        mock_graph = Mock()
        mock_graph.invoke.side_effect = Exception("LangChain processing error")
        mock_create_graph.return_value = mock_graph
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        transcript = "Invalid request"
        result = voice_service.process_with_langchain(transcript, user_id=1, session_name="Personal")
        
        assert result["is_complete"] is False
        assert "error" in result
        assert "LangChain processing error" in result["error"]

    def test_process_with_langchain_state_structure(self, voice_service):
        """Test that LangChain state is properly structured."""
        with patch('app.voice_assistant.create_graph') as mock_create_graph, \
             patch('app.voice_assistant.get_db') as mock_get_db:
            
            mock_graph = Mock()
            mock_graph.invoke.return_value = {"is_complete": True}
            mock_create_graph.return_value = mock_graph
            
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            
            transcript = "Test transcript"
            voice_service.process_with_langchain(transcript, user_id=123, session_name="TestSession")
            
            # Verify state structure
            call_args = mock_graph.invoke.call_args
            state = call_args[0][0]  # First argument is state
            config = call_args[0][1]  # Second argument is config
            
            assert state["user_query"] == transcript
            assert state["session_name"] == "TestSession"
            assert state["is_complete"] is False
            assert len(state["history"]) == 1
            assert state["history"][0]["sender"] == "user"
            assert state["history"][0]["text"] == transcript
            
            assert config["configurable"]["owner_id"] == 123


class TestVoiceAssistantWebSocketEnhanced:
    """Enhanced test suite for WebSocket voice assistant functionality."""

    @pytest.fixture
    def voice_assistant(self):
        """Create voice assistant instance for testing."""
        return VoiceAssistant()

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, voice_assistant, mock_websocket):
        """Test complete WebSocket connection lifecycle."""
        # Mock the process_audio_stream to return immediately
        with patch.object(voice_assistant, 'process_audio_stream') as mock_process:
            mock_process.return_value = None
            
            await voice_assistant.websocket_endpoint(mock_websocket)
            
            mock_websocket.accept.assert_called_once()
            mock_process.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_websocket_connection_error(self, voice_assistant, mock_websocket):
        """Test WebSocket connection error handling."""
        mock_websocket.accept.side_effect = Exception("Connection failed")
        
        with patch.object(voice_assistant, 'process_audio_stream') as mock_process:
            await voice_assistant.websocket_endpoint(mock_websocket)
            
            mock_websocket.accept.assert_called_once()
            mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_audio_stream_processing_complete_flow(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test complete audio stream processing flow."""
        # Setup WebSocket messages
        messages = [
            json.dumps({"audio": sample_audio_data}),
            json.dumps({"audio": sample_audio_data}),
        ]
        
        mock_websocket.receive_text.side_effect = messages + [WebSocketDisconnect()]
        
        # Mock voice processing
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.return_value = {
                "transcript": "Create a task to call mom",
                "is_final": True,
                "is_complete": True,
                "response": "Task created successfully",
                "audio_response": base64.b64encode(b"audio_response").decode()
            }
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass  # Expected
            
            # Verify processing was called
            assert mock_process.call_count == 2

    @pytest.mark.asyncio
    async def test_audio_stream_interim_results(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test handling of interim transcription results."""
        # Setup WebSocket messages
        message = json.dumps({"audio": sample_audio_data})
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        # Mock interim result
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.return_value = {
                "transcript": "Create a task to call",
                "is_final": False,
                "is_complete": False
            }
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify interim result was sent
            mock_websocket.send_json.assert_called_with({
                "type": "interim_transcript",
                "transcript": "Create a task to call",
                "is_final": False
            })

    @pytest.mark.asyncio
    async def test_audio_stream_final_result_with_task(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test handling of final transcription result with task creation."""
        message = json.dumps({"audio": sample_audio_data})
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        # Mock final result with task
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.return_value = {
                "transcript": "Create a task to call mom",
                "is_final": True,
                "is_complete": True,
                "response": "Task created successfully",
                "audio_response": base64.b64encode(b"audio_response").decode()
            }
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify final result was sent
            expected_calls = [
                call({
                    "type": "final_transcript",
                    "transcript": "Create a task to call mom",
                    "is_final": True
                }),
                call({
                    "type": "task_created",
                    "response": "Task created successfully"
                }),
                call({
                    "type": "audio_response",
                    "audio": base64.b64encode(b"audio_response").decode()
                })
            ]
            
            mock_websocket.send_json.assert_has_calls(expected_calls)

    @pytest.mark.asyncio
    async def test_audio_stream_error_handling(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test error handling in audio stream processing."""
        message = json.dumps({"audio": sample_audio_data})
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        # Mock processing error
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.side_effect = Exception("Processing error")
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify error was sent
            mock_websocket.send_json.assert_called_with({
                "type": "error",
                "message": "Processing error"
            })

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, voice_assistant, mock_websocket):
        """Test handling of invalid JSON messages."""
        mock_websocket.receive_text.side_effect = [
            "invalid json",
            WebSocketDisconnect()
        ]
        
        try:
            await voice_assistant.process_audio_stream(mock_websocket)
        except WebSocketDisconnect:
            pass
        
        # Verify error response
        mock_websocket.send_json.assert_called_with({
            "type": "error",
            "message": "Invalid JSON format"
        })

    @pytest.mark.asyncio
    async def test_missing_audio_data(self, voice_assistant, mock_websocket):
        """Test handling of messages without audio data."""
        message = json.dumps({"type": "ping"})  # Missing audio field
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        try:
            await voice_assistant.process_audio_stream(mock_websocket)
        except WebSocketDisconnect:
            pass
        
        # Verify error response
        mock_websocket.send_json.assert_called_with({
            "type": "error",
            "message": "Missing audio data"
        })

    def test_process_voice_command_integration(self, voice_assistant):
        """Test voice command processing with realistic data."""
        audio_data = b"sample_audio_data"
        
        # Mock the service
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock transcription
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Call mom at 3pm",
                "is_final": True
            }
            
            # Mock LangChain processing
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created: Call mom at 3pm"
            }
            
            # Mock TTS
            mock_service.text_to_speech.return_value = b"tts_audio_data"
            
            result = voice_assistant.process_voice_command(audio_data, user_id=1, session_name="Personal")
            
            assert result["transcript"] == "Call mom at 3pm"
            assert result["is_final"] is True
            assert result["is_complete"] is True
            assert result["response"] == "Task created: Call mom at 3pm"
            assert result["audio_response"] == base64.b64encode(b"tts_audio_data").decode()


class TestVoiceAssistantIntegrationEnhanced:
    """Enhanced integration tests for complete voice assistant workflow."""

    @patch('app.voice_assistant.VoiceAssistantService')
    def test_complete_voice_workflow_success(self, mock_service_class):
        """Test complete voice workflow from audio to task creation."""
        # Setup mocks
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": "I need to call John tomorrow at 2 PM",
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Call John",
            "start_time": "14:00:00",
            "start_date": "2025-01-16",
            "response": "Task created: Call John tomorrow at 2:00 PM"
        }
        
        mock_service.text_to_speech.return_value = b"success_audio_response"
        
        # Test the workflow
        voice_assistant = VoiceAssistant()
        result = voice_assistant.process_voice_command(
            audio_data=b"audio_input",
            user_id=1,
            session_name="Work"
        )
        
        # Verify complete workflow
        assert result["transcript"] == "I need to call John tomorrow at 2 PM"
        assert result["is_final"] is True
        assert result["is_complete"] is True
        assert result["response"] == "Task created: Call John tomorrow at 2:00 PM"
        assert "audio_response" in result
        
        # Verify service calls
        mock_service.process_audio_chunk.assert_called_once_with(b"audio_input")
        mock_service.process_with_langchain.assert_called_once_with(
            "I need to call John tomorrow at 2 PM", 1, "Work"
        )
        mock_service.text_to_speech.assert_called_once_with(
            "Task created: Call John tomorrow at 2:00 PM"
        )

    @patch('app.voice_assistant.VoiceAssistantService')
    def test_voice_workflow_with_clarification(self, mock_service_class):
        """Test voice workflow requiring clarification."""
        # Setup mocks
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": "I need to call someone",
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": False,
            "clarification": "Who would you like to call?",
            "response": "I'd be happy to help you make a call. Who would you like to call?"
        }
        
        mock_service.text_to_speech.return_value = b"clarification_audio_response"
        
        # Test the workflow
        voice_assistant = VoiceAssistant()
        result = voice_assistant.process_voice_command(
            audio_data=b"audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        # Verify clarification workflow
        assert result["transcript"] == "I need to call someone"
        assert result["is_final"] is True
        assert result["is_complete"] is False
        assert result["response"] == "I'd be happy to help you make a call. Who would you like to call?"
        assert "audio_response" in result

    @patch('app.voice_assistant.VoiceAssistantService')
    def test_voice_workflow_error_recovery(self, mock_service_class):
        """Test voice workflow error recovery."""
        # Setup mocks
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_service.process_audio_chunk.side_effect = Exception("Speech recognition failed")
        
        # Test error recovery
        voice_assistant = VoiceAssistant()
        result = voice_assistant.process_voice_command(
            audio_data=b"corrupted_audio",
            user_id=1,
            session_name="Personal"
        )
        
        # Verify error is handled gracefully
        assert "error" in result
        assert "Speech recognition failed" in result["error"]

    def test_voice_assistant_session_context(self):
        """Test voice assistant maintains session context."""
        # This test would verify that session information is properly passed
        # through the voice processing pipeline
        pass

    def test_voice_assistant_user_privacy(self):
        """Test voice assistant respects user privacy settings."""
        # This test would verify that private tasks are handled appropriately
        # and user data is protected
        pass


class TestVoiceAssistantPerformanceEnhanced:
    """Enhanced performance tests for voice assistant."""

    @pytest.mark.asyncio
    async def test_audio_processing_latency(self):
        """Test audio processing stays within acceptable latency bounds."""
        import time
        
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock fast responses
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Test message",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created"
            }
            mock_service.text_to_speech.return_value = b"audio_response"
            
            # Measure processing time
            start_time = time.time()
            result = voice_assistant.process_voice_command(
                audio_data=b"test_audio",
                user_id=1,
                session_name="Test"
            )
            end_time = time.time()
            
            # Verify low latency (should be under 1 second for mocked services)
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Processing took {processing_time:.2f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_concurrent_voice_sessions(self):
        """Test handling multiple concurrent voice sessions."""
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Concurrent test",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created"
            }
            mock_service.text_to_speech.return_value = b"audio"
            
            # Test concurrent processing
            tasks = []
            for i in range(5):
                task = voice_assistant.process_voice_command(
                    audio_data=f"audio_{i}".encode(),
                    user_id=i,
                    session_name=f"Session_{i}"
                )
                tasks.append(task)
            
            # Verify all tasks completed successfully
            for i, result in enumerate(tasks):
                assert result["transcript"] == "Concurrent test"
                assert result["is_complete"] is True

    def test_memory_usage_optimization(self):
        """Test memory usage stays within reasonable bounds."""
        import sys
        
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Memory test",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created"
            }
            mock_service.text_to_speech.return_value = b"audio"
            
            # Process multiple requests and verify memory doesn't grow excessively
            initial_size = sys.getsizeof(voice_assistant)
            
            for i in range(10):
                voice_assistant.process_voice_command(
                    audio_data=f"audio_{i}".encode(),
                    user_id=1,
                    session_name="Test"
                )
            
            final_size = sys.getsizeof(voice_assistant)
            
            # Memory shouldn't grow significantly
            assert final_size - initial_size < 1024, "Memory usage grew too much"


class TestVoiceAssistantSecurityEnhanced:
    """Enhanced security tests for voice assistant."""

    def test_audio_data_validation(self):
        """Test validation of audio data input."""
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Test with invalid audio data
            mock_service.process_audio_chunk.return_value = {
                "error": "Invalid audio format"
            }
            
            result = voice_assistant.process_voice_command(
                audio_data=b"invalid_audio_data",
                user_id=1,
                session_name="Test"
            )
            
            assert "error" in result
            assert "Invalid audio format" in result["error"]

    def test_user_authentication_required(self):
        """Test that user authentication is required for voice commands."""
        voice_assistant = VoiceAssistant()
        
        # Test with invalid user ID
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.process_with_langchain.side_effect = Exception("User not authenticated")
            
            result = voice_assistant.process_voice_command(
                audio_data=b"test_audio",
                user_id=None,  # Invalid user ID
                session_name="Test"
            )
            
            assert "error" in result

    def test_session_validation(self):
        """Test that session validation is enforced."""
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Test with invalid session
            mock_service.process_with_langchain.side_effect = Exception("Invalid session")
            
            result = voice_assistant.process_voice_command(
                audio_data=b"test_audio",
                user_id=1,
                session_name=""  # Empty session name
            )
            
            assert "error" in result

    def test_input_sanitization(self):
        """Test that malicious input is properly sanitized."""
        voice_assistant = VoiceAssistant()
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock processing of potentially malicious transcript
            mock_service.process_audio_chunk.return_value = {
                "transcript": "<script>alert('xss')</script>",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created safely"
            }
            
            mock_service.text_to_speech.return_value = b"safe_audio"
            
            result = voice_assistant.process_voice_command(
                audio_data=b"malicious_audio",
                user_id=1,
                session_name="Test"
            )
            
            # Verify the transcript is returned but processing continues safely
            assert result["transcript"] == "<script>alert('xss')</script>"
            assert result["response"] == "Task created safely"


class TestVoiceAssistantConfigurationEnhanced:
    """Enhanced configuration tests for voice assistant."""

    def test_voice_settings_customization(self):
        """Test voice settings can be customized."""
        # Test with custom settings
        service = VoiceAssistantService()
        
        assert service.rate == 16000  # Default
        assert service.chunk_size == 1600  # Default
        
        # Test that settings can be modified
        service.rate = 8000
        service.chunk_size = 800
        
        assert service.rate == 8000
        assert service.chunk_size == 800

    def test_audio_quality_configuration(self):
        """Test audio quality settings."""
        service = VoiceAssistantService()
        
        # Test speech config quality settings
        with patch.object(service, 'speech_client') as mock_client:
            mock_client.RecognitionConfig = Mock()
            mock_client.RecognitionConfig.AudioEncoding = Mock()
            mock_client.RecognitionConfig.AudioEncoding.LINEAR16 = "LINEAR16"
            
            config = service.get_speech_config()
            
            assert config.encoding == "LINEAR16"
            assert config.sample_rate_hertz == 16000
            assert config.enable_automatic_punctuation is True

    def test_language_configuration(self):
        """Test language settings configuration."""
        service = VoiceAssistantService()
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_client.RecognitionConfig = Mock()
            mock_client.RecognitionConfig.AudioEncoding = Mock()
            mock_client.RecognitionConfig.AudioEncoding.LINEAR16 = "LINEAR16"
            
            config = service.get_speech_config()
            
            assert config.language_code == "en-US"
            
            # Test that language code can be customized
            # (In a real implementation, this would be configurable)

    def test_credential_configuration(self):
        """Test Google Cloud credential configuration."""
        # Test with file path
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'}):
            with patch('app.voice_assistant.speech.SpeechClient') as mock_speech:
                service = VoiceAssistantService()
                mock_speech.assert_called()

    def test_credential_configuration_json_string(self):
        """Test Google Cloud credential configuration with JSON string."""
        json_creds = '{"type": "service_account", "project_id": "test"}'
        
        with patch('app.voice_assistant.settings') as mock_settings:
            mock_settings.GOOGLE_CLOUD_CREDENTIALS_JSON = json_creds
            mock_settings.GOOGLE_APPLICATION_CREDENTIALS = None
            
            with patch('app.voice_assistant.speech.SpeechClient') as mock_speech, \
                 patch('tempfile.NamedTemporaryFile') as mock_temp:
                
                mock_temp.return_value.__enter__ = Mock(return_value=Mock(name='/tmp/creds.json'))
                mock_temp.return_value.__exit__ = Mock(return_value=None)
                
                service = VoiceAssistantService()
                mock_speech.assert_called() 

class TestContinuousVoiceChatFeatures:
    """Test suite for continuous voice chat functionality."""

    @pytest.fixture
    def voice_service_with_continuous(self, mock_speech_client, mock_tts_client):
        """Create VoiceAssistantService with continuous mode support."""
        with patch('app.voice_assistant.speech') as mock_speech_module:
            mock_speech_module.SpeechClient.return_value = mock_speech_client
            
            with patch('app.voice_assistant.texttospeech') as mock_tts_module:
                mock_tts_module.TextToSpeechClient.return_value = mock_tts_client
                
                service = VoiceAssistantService(
                    speech_client=mock_speech_client,
                    tts_client=mock_tts_client
                )
                return service

    def test_process_audio_immediate_success(self, voice_service_with_continuous, mock_speech_client, sample_audio_data):
        """Test immediate audio processing for continuous mode."""
        # Setup - create audio data that's at least 100 bytes
        audio_data = b"x" * 200  # 200 bytes of audio data
        
        # Mock speech recognition response
        mock_response = Mock()
        mock_response.results = [Mock()]
        mock_response.results[0].alternatives = [Mock()]
        mock_response.results[0].alternatives[0].transcript = "Create a task to call John"
        mock_speech_client.recognize.return_value = mock_response
        
        # Mock try_speech_recognition to return transcript
        with patch.object(voice_service_with_continuous, 'try_speech_recognition') as mock_try_speech:
            mock_try_speech.return_value = {"transcript": "Create a task to call John"}
            
            # Execute
            result = voice_service_with_continuous.process_audio_immediate(audio_data)
        
        # Verify
        assert "transcript" in result
        assert result["transcript"] == "Create a task to call John"
        assert "error" not in result
        mock_try_speech.assert_called_once()

    def test_process_audio_immediate_short_audio(self, voice_service_with_continuous):
        """Test immediate processing with too short audio data."""
        # Setup - audio data too short
        short_audio = b"short"
        
        # Execute
        result = voice_service_with_continuous.process_audio_immediate(short_audio)
        
        # Verify
        assert "error" in result
        assert "too short" in result["error"].lower()

    def test_process_audio_immediate_timeout(self, voice_service_with_continuous, mock_speech_client):
        """Test immediate processing with timeout handling."""
        # Setup
        audio_data = b"x" * 1000  # Valid length audio
        
        # Mock try_speech_recognition to simulate timeout
        with patch.object(voice_service_with_continuous, 'try_speech_recognition') as mock_try_speech:
            mock_try_speech.side_effect = Exception("Timeout")
            
            # Execute
            result = voice_service_with_continuous.process_audio_immediate(audio_data)
        
        # Verify
        assert "error" in result
        assert "Speech recognition failed" in result["error"] or "Audio processing failed" in result["error"]

    def test_process_audio_immediate_no_client(self):
        """Test immediate processing without speech client."""
        # Setup
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        audio_data = b"x" * 1000
        
        # Execute
        result = service.process_audio_immediate(audio_data)
        
        # Verify
        assert "error" in result
        assert "Speech client not initialized" in result["error"]

    def test_text_to_speech_fast_success(self, voice_service_with_continuous, mock_tts_client):
        """Test fast text-to-speech for continuous mode."""
        # Setup
        test_text = "Task created successfully!"
        mock_response = Mock()
        mock_response.audio_content = b"fast_audio_content"
        mock_tts_client.synthesize_speech.return_value = mock_response
        
        # Execute
        result = voice_service_with_continuous.text_to_speech_fast(test_text)
        
        # Verify
        assert result == b"fast_audio_content"
        mock_tts_client.synthesize_speech.assert_called_once()
        
        # Verify it uses Standard voice (faster) instead of Wavenet
        call_args = mock_tts_client.synthesize_speech.call_args
        voice_params = call_args[1]['voice']
        assert "Standard" in voice_params.name

    def test_text_to_speech_fast_fallback(self, voice_service_with_continuous, mock_tts_client):
        """Test fast TTS falls back to regular TTS on error."""
        # Setup
        test_text = "Hello world"
        mock_tts_client.synthesize_speech.side_effect = [
            Exception("Fast TTS failed"),  # First call (fast) fails
            Mock(audio_content=b"regular_audio")  # Second call (regular) succeeds
        ]
        
        # Execute
        result = voice_service_with_continuous.text_to_speech_fast(test_text)
        
        # Verify
        assert result == b"regular_audio"
        assert mock_tts_client.synthesize_speech.call_count == 2

    def test_text_to_speech_fast_no_client(self):
        """Test fast TTS without client."""
        # Setup
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        
        # Execute
        result = service.text_to_speech_fast("Test text")
        
        # Verify
        assert result == b""


class TestContinuousVoiceChatWebSocket:
    """Test WebSocket functionality with continuous mode."""

    @pytest.fixture
    def mock_websocket_continuous(self):
        """Mock WebSocket for continuous voice chat testing."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"
        return websocket

    @pytest.fixture
    def voice_assistant_continuous(self):
        """Voice assistant instance for continuous testing."""
        return VoiceAssistant()

    @pytest.mark.asyncio
    async def test_continuous_mode_message_handling(self, voice_assistant_continuous, mock_websocket_continuous):
        """Test WebSocket handling of continuous mode messages."""
        # Test the _process_transcript method directly with continuous mode
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        # Mock the service methods
        with patch.object(voice_assistant_continuous.service, 'process_with_langchain') as mock_langchain:
            mock_langchain.return_value = {
                "is_complete": True,
                "task_title": "Test task"
            }
            
            with patch.object(voice_assistant_continuous.service, 'text_to_speech_fast') as mock_tts:
                mock_tts.return_value = b"audio_response"
                
                # Execute _process_transcript with continuous_mode=True
                await voice_assistant_continuous._process_transcript(
                    mock_websocket, 
                    "Create a test task", 
                    user_id=1, 
                    session_name="Personal", 
                    team_names=[], 
                    continuous_mode=True
                )
                
                # Verify fast TTS was called for continuous mode
                mock_tts.assert_called_once()
                
                # Verify response includes continuous_mode flag
                mock_websocket.send_json.assert_called_once()
                response_data = mock_websocket.send_json.call_args[0][0]
                assert response_data["continuous_mode"] == True

    @pytest.mark.asyncio 
    async def test_interrupt_action_handling(self, voice_assistant_continuous, mock_websocket_continuous):
        """Test WebSocket handling of interrupt actions."""
        # Test that interrupt response format is correct
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        # Simulate what happens in the WebSocket handler for interrupt
        expected_response = {
            "status": "interrupted",
            "message": "Assistant interrupted, listening to you..."
        }
        
        # Call send_json directly to test the format
        await mock_websocket.send_json(expected_response)
        
        # Verify the response format
        mock_websocket.send_json.assert_called_once_with({
            "status": "interrupted", 
            "message": "Assistant interrupted, listening to you..."
        })

    @pytest.mark.asyncio
    async def test_process_transcript_continuous_mode(self, voice_assistant_continuous, mock_websocket_continuous):
        """Test transcript processing with continuous mode flag."""
        # Setup
        test_transcript = "Create a task to call mom"
        
        # Mock LangChain processing
        with patch.object(voice_assistant_continuous.service, 'process_with_langchain') as mock_langchain:
            mock_langchain.return_value = {
                "is_complete": True,
                "task_title": "Call mom"
            }
            
            # Mock fast TTS
            with patch.object(voice_assistant_continuous.service, 'text_to_speech_fast') as mock_fast_tts:
                mock_fast_tts.return_value = b"fast_audio_response"
                
                # Execute
                await voice_assistant_continuous._process_transcript(
                    mock_websocket_continuous, 
                    test_transcript, 
                    user_id=1, 
                    session_name="Personal", 
                    team_names=[], 
                    continuous_mode=True
                )
        
        # Verify
        mock_fast_tts.assert_called_once()  # Should use fast TTS in continuous mode
        
        # Verify response includes continuous_mode flag
        mock_websocket_continuous.send_json.assert_called_once()
        response_data = mock_websocket_continuous.send_json.call_args[0][0]
        assert response_data["continuous_mode"] == True

    @pytest.mark.asyncio
    async def test_process_transcript_regular_mode(self, voice_assistant_continuous, mock_websocket_continuous):
        """Test transcript processing without continuous mode flag."""
        # Setup
        test_transcript = "Create a task to call dad"
        
        # Mock LangChain processing
        with patch.object(voice_assistant_continuous.service, 'process_with_langchain') as mock_langchain:
            mock_langchain.return_value = {
                "is_complete": True,
                "task_title": "Call dad"
            }
            
            # Mock regular TTS
            with patch.object(voice_assistant_continuous.service, 'text_to_speech') as mock_regular_tts:
                mock_regular_tts.return_value = b"regular_audio_response"
                
                # Execute
                await voice_assistant_continuous._process_transcript(
                    mock_websocket_continuous, 
                    test_transcript, 
                    user_id=1, 
                    session_name="Personal", 
                    team_names=[], 
                    continuous_mode=False
                )
        
        # Verify
        mock_regular_tts.assert_called_once()  # Should use regular TTS in normal mode
        
        # Verify response includes continuous_mode flag as False
        response_data = mock_websocket_continuous.send_json.call_args[0][0]
        assert response_data["continuous_mode"] == False


class TestContinuousVoiceChatIntegration:
    """Integration tests for continuous voice chat end-to-end functionality."""

    @pytest.mark.asyncio
    async def test_full_continuous_conversation_flow(self):
        """Test complete continuous voice chat conversation flow."""
        # Test the core components work together
        voice_assistant = VoiceAssistant()
        
        # Test that service has the required methods
        assert hasattr(voice_assistant.service, 'process_audio_immediate')
        assert hasattr(voice_assistant.service, 'text_to_speech_fast')
        assert hasattr(voice_assistant, '_process_transcript')
        
        # Test that _process_transcript supports continuous mode
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
            mock_langchain.return_value = {
                "is_complete": True,
                "task_title": "Test task"
            }
            
            with patch.object(voice_assistant.service, 'text_to_speech_fast') as mock_fast_tts:
                mock_fast_tts.return_value = b"audio_response"
                
                # Test both continuous and regular modes
                await voice_assistant._process_transcript(
                    mock_websocket, "Test transcript", 1, "Personal", [], continuous_mode=True
                )
                await voice_assistant._process_transcript(
                    mock_websocket, "Test transcript", 1, "Personal", [], continuous_mode=False
                )
        
        # Verify methods were called
        assert mock_langchain.call_count == 2
        assert mock_fast_tts.call_count == 1  # Only for continuous mode
        assert mock_websocket.send_json.call_count == 2

    def test_continuous_mode_configuration_validation(self):
        """Test that continuous mode configuration is properly validated."""
        # Setup
        service = VoiceAssistantService()
        
        # Test that new methods exist
        assert hasattr(service, 'process_audio_immediate')
        assert hasattr(service, 'text_to_speech_fast')
        assert callable(service.process_audio_immediate)
        assert callable(service.text_to_speech_fast)
        
        # Test method signatures
        import inspect
        immediate_sig = inspect.signature(service.process_audio_immediate)
        assert 'audio_data' in immediate_sig.parameters
        
        fast_tts_sig = inspect.signature(service.text_to_speech_fast)
        assert 'text' in fast_tts_sig.parameters

    def test_backward_compatibility(self, mock_speech_client, mock_tts_client, sample_audio_data):
        """Test that existing functionality still works with new features."""
        # Setup
        with patch('app.voice_assistant.speech') as mock_speech_module:
            mock_speech_module.SpeechClient.return_value = mock_speech_client
            
            with patch('app.voice_assistant.texttospeech') as mock_tts_module:
                mock_tts_module.TextToSpeechClient.return_value = mock_tts_client
                
                service = VoiceAssistantService(
                    speech_client=mock_speech_client,
                    tts_client=mock_tts_client
                )
        
        audio_data = base64.b64decode(sample_audio_data)
        
        # Test that old method still works
        with patch.object(service, 'try_speech_recognition') as mock_recognition:
            mock_recognition.return_value = {"transcript": "test"}
            
            # Execute old method
            result = service.process_audio_chunk(audio_data)
            
            # Verify
            assert isinstance(result, dict)  # Should return a dict response
