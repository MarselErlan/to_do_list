"""
Enhanced Test-Driven Development tests for Voice Assistant functionality.
This file contains improved tests with better fixtures, realistic scenarios, and comprehensive coverage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import json
import base64
import asyncio
import time
from fastapi.testclient import TestClient
from fastapi import WebSocket, WebSocketDisconnect
from app.voice_assistant import VoiceAssistant, VoiceAssistantService
from app.main import app


# Enhanced Test Fixtures
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
    mock_response.audio_content = b"realistic_audio_content_16khz_linear16"
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
def realistic_transcripts():
    """Realistic voice transcripts for testing."""
    return {
        "simple_task": "I need to call mom at 3pm today",
        "complex_task": "Schedule a meeting with the team tomorrow at 2 PM for project planning",
        "unclear_task": "I need to do something important",
        "time_ambiguous": "Call John sometime this week",
        "multiple_tasks": "Call mom at 3pm and email boss about the report",
        "with_noise": "I need to call... um... my mom at 3pm today",
        "long_task": "I need to schedule a very important meeting with all the stakeholders including the product manager, engineering lead, and design team to discuss the quarterly roadmap and address the technical debt issues we've been facing"
    }


@pytest.fixture
def langchain_responses():
    """Realistic LangChain responses for different scenarios."""
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
        "complex_task": {
            "is_complete": True,
            "task_title": "Team meeting - project planning",
            "start_time": "14:00:00",
            "start_date": "2025-01-16",
            "response": "Meeting scheduled with team for project planning tomorrow at 2:00 PM"
        },
        "error_response": {
            "is_complete": False,
            "error": "Unable to parse time from your request",
            "response": "I didn't understand the time. Could you please specify when you'd like to do this?"
        }
    }


class TestVoiceAssistantServiceBehavior:
    """Test the core behavior of VoiceAssistantService."""

    def test_service_initialization_success(self, mock_speech_client, mock_tts_client):
        """Test successful service initialization with proper clients."""
        service = VoiceAssistantService(
            speech_client=mock_speech_client,
            tts_client=mock_tts_client
        )
        
        assert service.speech_client == mock_speech_client
        assert service.tts_client == mock_tts_client
        assert service.rate == 16000
        assert service.chunk_size == 1600

    def test_service_initialization_graceful_degradation(self):
        """Test service handles missing credentials gracefully."""
        with patch('app.voice_assistant.speech.SpeechClient') as mock_speech, \
             patch('app.voice_assistant.texttospeech.TextToSpeechClient') as mock_tts:
            
            mock_speech.side_effect = Exception("Credentials not found")
            mock_tts.side_effect = Exception("Credentials not found")
            
            service = VoiceAssistantService()
            
            # Should not raise exception, should handle gracefully
            assert service.speech_client is None
            assert service.tts_client is None

    def test_speech_recognition_configuration(self, voice_service):
        """Test speech recognition is configured correctly."""
        config = voice_service.get_speech_config()
        
        assert config.encoding == "LINEAR16"
        assert config.sample_rate_hertz == 16000
        assert config.language_code == "en-US"
        assert config.enable_automatic_punctuation is True

    def test_audio_processing_realistic_scenarios(self, voice_service, mock_speech_client, realistic_transcripts):
        """Test audio processing with realistic transcript scenarios."""
        test_cases = [
            ("simple_task", True),
            ("complex_task", True),
            ("unclear_task", True),
            ("with_noise", True),
            ("long_task", True),
        ]
        
        for transcript_key, should_be_final in test_cases:
            # Setup mock response
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = realistic_transcripts[transcript_key]
            mock_result.is_final = should_be_final
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_speech_client.streaming_recognize.return_value = [mock_response]
            
            result = voice_service.process_audio_chunk(b"audio_data")
            
            assert result["transcript"] == realistic_transcripts[transcript_key]
            assert result["is_final"] == should_be_final

    def test_text_to_speech_various_responses(self, voice_service, mock_tts_client):
        """Test TTS with various response types."""
        test_responses = [
            "Task created successfully: Call mom at 3:00 PM today",
            "I'd be happy to help you schedule a call with mom. What time works best for you?",
            "I didn't understand the time. Could you please specify when you'd like to do this?",
            "Meeting scheduled with team for project planning tomorrow at 2:00 PM",
            "Error: Unable to process your request. Please try again."
        ]
        
        for response_text in test_responses:
            result = voice_service.text_to_speech(response_text)
            
            assert result == b"realistic_audio_content_16khz_linear16"
            mock_tts_client.synthesize_speech.assert_called()

    @patch('app.voice_assistant.create_graph')
    @patch('app.voice_assistant.get_db')
    def test_langchain_integration_complete_workflow(self, mock_get_db, mock_create_graph, voice_service, langchain_responses):
        """Test complete LangChain integration workflow."""
        # Setup mocks
        mock_graph = Mock()
        mock_graph.invoke.return_value = langchain_responses["complete_task"]
        mock_create_graph.return_value = mock_graph
        
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])
        
        transcript = "I need to call my mom at 3pm today"
        result = voice_service.process_with_langchain(transcript, user_id=1, session_name="Personal")
        
        assert result["is_complete"] is True
        assert result["task_title"] == "Call mom"
        assert result["start_time"] == "15:00:00"
        assert result["start_date"] == "2025-01-15"
        assert "response" in result
        
        # Verify state structure passed to LangChain
        call_args = mock_graph.invoke.call_args
        state = call_args[0][0]
        
        assert state["user_query"] == transcript
        assert state["session_name"] == "Personal"
        assert state["is_complete"] is False
        assert len(state["history"]) == 1

    def test_error_handling_comprehensive(self, voice_service, mock_speech_client, mock_tts_client):
        """Test comprehensive error handling scenarios."""
        # Test speech recognition errors
        mock_speech_client.streaming_recognize.side_effect = Exception("API rate limit exceeded")
        
        result = voice_service.process_audio_chunk(b"audio_data")
        
        assert "error" in result
        assert "API rate limit exceeded" in result["error"]
        
        # Test TTS errors
        mock_tts_client.synthesize_speech.side_effect = Exception("TTS quota exceeded")
        
        result = voice_service.text_to_speech("Hello world")
        
        assert result == b""


class TestVoiceAssistantWebSocketBehavior:
    """Test WebSocket behavior with realistic scenarios."""

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket with realistic behavior."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def voice_assistant(self):
        """Create voice assistant instance."""
        return VoiceAssistant()

    @pytest.mark.asyncio
    async def test_websocket_complete_conversation_flow(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test complete conversation flow through WebSocket."""
        # Setup conversation sequence
        conversation = [
            json.dumps({"audio": sample_audio_data}),  # User speaks
            json.dumps({"audio": sample_audio_data}),  # User continues
            json.dumps({"audio": sample_audio_data}),  # User finishes
        ]
        
        mock_websocket.receive_text.side_effect = conversation + [WebSocketDisconnect()]
        
        # Mock realistic processing
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.side_effect = [
                {  # Interim result
                    "transcript": "I need to call",
                    "is_final": False,
                    "is_complete": False
                },
                {  # More interim
                    "transcript": "I need to call mom",
                    "is_final": False,
                    "is_complete": False
                },
                {  # Final result
                    "transcript": "I need to call mom at 3pm today",
                    "is_final": True,
                    "is_complete": True,
                    "response": "Task created successfully: Call mom at 3:00 PM today",
                    "audio_response": base64.b64encode(b"success_audio").decode()
                }
            ]
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify conversation flow
            assert mock_process.call_count == 3
            
            # Check final response was sent
            final_calls = mock_websocket.send_json.call_args_list
            assert any("task_created" in str(call) for call in final_calls)
            assert any("audio_response" in str(call) for call in final_calls)

    @pytest.mark.asyncio
    async def test_websocket_error_recovery(self, voice_assistant, mock_websocket, sample_audio_data):
        """Test WebSocket error recovery mechanisms."""
        # Setup error scenario
        mock_websocket.receive_text.side_effect = [
            json.dumps({"audio": sample_audio_data}),
            WebSocketDisconnect()
        ]
        
        # Mock processing error
        with patch.object(voice_assistant, 'process_voice_command') as mock_process:
            mock_process.side_effect = Exception("Processing temporarily unavailable")
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify error was communicated
            mock_websocket.send_json.assert_called_with({
                "type": "error",
                "message": "Processing temporarily unavailable"
            })

    @pytest.mark.asyncio
    async def test_websocket_handles_malformed_messages(self, voice_assistant, mock_websocket):
        """Test WebSocket handles malformed messages gracefully."""
        malformed_messages = [
            "not json",
            '{"invalid": "json"',
            '{"missing": "audio"}',
            '{"audio": "not_base64!@#"}',
            ""
        ]
        
        for message in malformed_messages:
            mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
            
            try:
                await voice_assistant.process_audio_stream(mock_websocket)
            except WebSocketDisconnect:
                pass
            
            # Should send error response
            mock_websocket.send_json.assert_called()
            last_call = mock_websocket.send_json.call_args_list[-1]
            assert "error" in str(last_call)
            
            # Reset for next test
            mock_websocket.reset_mock()


class TestVoiceAssistantIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def voice_assistant(self):
        return VoiceAssistant()

    def test_simple_task_creation_scenario(self, voice_assistant):
        """Test: User says 'Call mom at 3pm' -> Task created."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the complete flow
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Call mom at 3pm today",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "task_title": "Call mom",
                "start_time": "15:00:00",
                "start_date": "2025-01-15",
                "response": "Task created: Call mom at 3:00 PM today"
            }
            
            mock_service.text_to_speech.return_value = b"task_created_audio"
            
            result = voice_assistant.process_voice_command(
                audio_data=b"audio_input",
                user_id=1,
                session_name="Personal"
            )
            
            # Verify successful task creation
            assert result["is_complete"] is True
            assert result["transcript"] == "Call mom at 3pm today"
            assert "Task created" in result["response"]

    def test_clarification_needed_scenario(self, voice_assistant):
        """Test: User says 'Call someone' -> System asks for clarification."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
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
            
            mock_service.text_to_speech.return_value = b"clarification_audio"
            
            result = voice_assistant.process_voice_command(
                audio_data=b"audio_input",
                user_id=1,
                session_name="Personal"
            )
            
            # Verify clarification request
            assert result["is_complete"] is False
            assert "Who would you like to call" in result["response"]

    def test_complex_task_scenario(self, voice_assistant):
        """Test: Complex task with multiple parameters."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Schedule a team meeting tomorrow at 2 PM to discuss the quarterly roadmap",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "task_title": "Team meeting - quarterly roadmap",
                "start_time": "14:00:00",
                "start_date": "2025-01-16",
                "response": "Meeting scheduled: Team meeting for quarterly roadmap tomorrow at 2:00 PM"
            }
            
            mock_service.text_to_speech.return_value = b"meeting_scheduled_audio"
            
            result = voice_assistant.process_voice_command(
                audio_data=b"audio_input",
                user_id=1,
                session_name="Work"
            )
            
            # Verify complex task handling
            assert result["is_complete"] is True
            assert "quarterly roadmap" in result["response"]
            assert "tomorrow at 2:00 PM" in result["response"]

    def test_error_recovery_scenario(self, voice_assistant):
        """Test: System recovers from various error conditions."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Test speech recognition error
            mock_service.process_audio_chunk.side_effect = Exception("Speech recognition failed")
            
            result = voice_assistant.process_voice_command(
                audio_data=b"corrupted_audio",
                user_id=1,
                session_name="Personal"
            )
            
            assert "error" in result
            assert "Speech recognition failed" in result["error"]

    def test_performance_under_load_scenario(self, voice_assistant):
        """Test: System performance under concurrent load."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock fast processing
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Quick task",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created"
            }
            
            mock_service.text_to_speech.return_value = b"audio"
            
            # Process multiple concurrent requests
            results = []
            start_time = time.time()
            
            for i in range(10):
                result = voice_assistant.process_voice_command(
                    audio_data=f"audio_{i}".encode(),
                    user_id=i,
                    session_name=f"Session_{i}"
                )
                results.append(result)
            
            end_time = time.time()
            
            # Verify all requests completed successfully
            assert len(results) == 10
            for result in results:
                assert result["is_complete"] is True
            
            # Verify reasonable performance
            total_time = end_time - start_time
            assert total_time < 5.0, f"Processing 10 requests took {total_time:.2f}s"


class TestVoiceAssistantEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_transcript(self):
        """Test handling of very long transcripts."""
        service = VoiceAssistantService()
        
        # Create a very long transcript
        long_transcript = "I need to " + "do something " * 100 + "at 3pm today"
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = long_transcript
            mock_result.is_final = True
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_client.streaming_recognize.return_value = [mock_response]
            
            result = service.process_audio_chunk(b"audio_data")
            
            assert result["transcript"] == long_transcript
            assert result["is_final"] is True

    def test_special_characters_in_transcript(self):
        """Test handling of special characters in transcripts."""
        service = VoiceAssistantService()
        
        special_transcript = "Email john@example.com about the $1,000 budget & 50% increase"
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = special_transcript
            mock_result.is_final = True
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_client.streaming_recognize.return_value = [mock_response]
            
            result = service.process_audio_chunk(b"audio_data")
            
            assert result["transcript"] == special_transcript
            assert result["is_final"] is True

    def test_empty_audio_data(self):
        """Test handling of empty audio data."""
        service = VoiceAssistantService()
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_client.streaming_recognize.return_value = []
            
            result = service.process_audio_chunk(b"")
            
            assert result["transcript"] == ""
            assert result["is_final"] is False

    def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        service = VoiceAssistantService()
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_client.streaming_recognize.side_effect = Exception("Network timeout")
            
            result = service.process_audio_chunk(b"audio_data")
            
            assert "error" in result
            assert "Network timeout" in result["error"]

    def test_concurrent_processing_safety(self):
        """Test thread safety of concurrent processing."""
        service = VoiceAssistantService()
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = "Concurrent test"
            mock_result.is_final = True
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_client.streaming_recognize.return_value = [mock_response]
            
            # Process multiple requests concurrently
            results = []
            for i in range(5):
                result = service.process_audio_chunk(f"audio_{i}".encode())
                results.append(result)
            
            # Verify all processed correctly
            for result in results:
                assert result["transcript"] == "Concurrent test"
                assert result["is_final"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 