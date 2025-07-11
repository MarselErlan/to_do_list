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
from app.config import settings
from google.cloud import speech


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
        
        assert config.encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
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
        
        for transcript_key, _ in test_cases:
            # Setup mock response
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = realistic_transcripts[transcript_key]
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_speech_client.recognize.return_value = mock_response
            
            result = voice_service.process_audio_immediate(b"audio_data" * 20) # ensure long enough
            
            assert result["transcript"] == realistic_transcripts[transcript_key]

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
        mock_speech_client.recognize.side_effect = Exception("API rate limit exceeded")
        
        result = voice_service.process_audio_immediate(b"audio_data" * 20)
        
        assert "error" in result
        assert "No speech detected" in result["error"]
        
        # Test TTS errors
        mock_tts_client.synthesize_speech.side_effect = Exception("TTS quota exceeded")
        
        result = voice_service.text_to_speech("Hello world")
        
        assert result == b""


class TestVoiceAssistantIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_simple_task_creation_scenario(self):
        """Test: User says 'Call mom at 3pm' -> Task created."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
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
            mock_service_class.return_value = mock_service
            
            voice_assistant = VoiceAssistant()
            result = voice_assistant.process_voice_command(
                b"audio_input", 1, "Personal"
            )
            
            assert result["is_complete"] is True
            assert result["response"] == "Task created: Call mom at 3:00 PM today"

    def test_clarification_needed_scenario(self):
        """Test: User says 'Call mom' -> Clarification requested."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Call mom",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": False,
                "clarification": "What time would you like to call?",
                "response": "When would you like to call mom?"
            }
            mock_service.text_to_speech.return_value = b"clarification_audio"
            mock_service_class.return_value = mock_service
            
            voice_assistant = VoiceAssistant()
            result = voice_assistant.process_voice_command(
                b"audio_input", 1, "Personal"
            )
            
            assert result["is_complete"] is False
            assert "clarification" in result

    def test_complex_task_scenario(self):
        """Test: User gives a complex command -> Task created."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Remind me to submit the report by 5 PM on Friday",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "task_title": "Submit report",
                "start_time": "17:00:00",
                "start_date": "2025-01-17",
                "response": "Reminder set: Submit report by 5:00 PM on Friday"
            }
            mock_service.text_to_speech.return_value = b"complex_task_audio"
            mock_service_class.return_value = mock_service
            
            voice_assistant = VoiceAssistant()
            result = voice_assistant.process_voice_command(
                b"audio_input", 1, "Work"
            )
            
            assert result["is_complete"] is True
            assert "Submit report" in result["task_title"]

    def test_error_recovery_scenario(self):
        """Test: Speech recognition fails -> Graceful error returned."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_audio_chunk.return_value = {
                "error": "Speech recognition failed"
            }
            mock_service_class.return_value = mock_service
            
            voice_assistant = VoiceAssistant()
            result = voice_assistant.process_voice_command(
                b"corrupted_audio", 1, "Personal"
            )
            
            assert "error" in result

    def test_performance_under_load_scenario(self):
        """Test: System handles high load without crashing."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Test",
                "is_final": True
            }
            mock_service.process_with_langchain.return_value = {
                "is_complete": True
            }
            mock_service.text_to_speech.return_value = b"audio"
            mock_service_class.return_value = mock_service
            
            voice_assistant = VoiceAssistant()
            
            # Simulate multiple quick requests
            for _ in range(5):
                result = voice_assistant.process_voice_command(
                    b"audio_input", 1, "LoadTest"
                )
                assert "is_complete" in result


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
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_client.recognize.return_value = mock_response
            
            result = service.process_audio_immediate(b"very_long_audio" * 50)
            
            assert result["transcript"] == long_transcript

    def test_special_characters_in_transcript(self):
        """Test handling of special characters and emojis."""
        service = VoiceAssistantService()
        transcript = "Call John 🚀 @ 3pm! #urgent"
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_result = Mock()
            mock_result.alternatives = [Mock()]
            mock_result.alternatives[0].transcript = transcript
            
            mock_response = Mock()
            mock_response.results = [mock_result]
            
            mock_client.recognize.return_value = mock_response
            
            result = service.process_audio_immediate(b"audio_with_special_chars" * 20)
            
            assert result["transcript"] == transcript

    def test_empty_audio_data(self):
        """Test handling of empty audio data submission."""
        service = VoiceAssistantService(speech_client=Mock())
        result = service.process_audio_immediate(b"")
        
        assert "error" in result
        assert "Audio data too short" in result["error"]

    def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        service = VoiceAssistantService(speech_client=Mock())
        
        with patch.object(service, 'speech_client') as mock_client:
            mock_client.recognize.side_effect = Exception("Network timeout")
            
            result = service.process_audio_immediate(b"audio_data" * 20)
            
            assert "error" in result
            assert "No speech detected" in result["error"]

    def test_concurrent_processing_safety(self):
        """Test for race conditions with concurrent processing (conceptual)."""
        # This test is conceptual and would be hard to implement without a
        # running service. It would involve making concurrent requests and
        # checking for unexpected state changes.
        pass 