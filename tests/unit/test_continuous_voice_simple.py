"""
Simple tests for continuous voice chat functionality.
Focus on core functionality without complex WebSocket mocking.
"""

import pytest
from unittest.mock import Mock, patch
import base64
from app.voice_assistant import VoiceAssistant, VoiceAssistantService


class TestContinuousVoiceChatCore:
    """Test core continuous voice chat functionality."""

    def test_process_audio_immediate_exists(self):
        """Test that process_audio_immediate method exists and is callable."""
        service = VoiceAssistantService()
        assert hasattr(service, 'process_audio_immediate')
        assert callable(service.process_audio_immediate)

    def test_text_to_speech_fast_exists(self):
        """Test that text_to_speech_fast method exists and is callable."""
        service = VoiceAssistantService()
        assert hasattr(service, 'text_to_speech_fast')
        assert callable(service.text_to_speech_fast)

    def test_process_audio_immediate_short_audio(self):
        """Test process_audio_immediate with short audio."""
        # Create service with mock client to bypass credential issues
        mock_client = Mock()
        service = VoiceAssistantService(speech_client=mock_client)
        short_audio = b"short"
        
        result = service.process_audio_immediate(short_audio)
        
        assert "error" in result
        assert "too short" in result["error"].lower()

    def test_process_audio_immediate_no_client(self):
        """Test process_audio_immediate without speech client."""
        service = VoiceAssistantService(speech_client=None)
        audio_data = b"x" * 200  # Valid length
        
        result = service.process_audio_immediate(audio_data)
        
        assert "error" in result
        assert "speech client" in result["error"].lower()

    def test_text_to_speech_fast_no_client(self):
        """Test text_to_speech_fast without TTS client."""
        service = VoiceAssistantService(tts_client=None)
        
        result = service.text_to_speech_fast("Hello world")
        
        assert result == b""

    def test_process_audio_immediate_with_mock_client(self):
        """Test process_audio_immediate with mocked client."""
        mock_client = Mock()
        service = VoiceAssistantService(speech_client=mock_client)
        
        # Mock the recognition method
        with patch.object(service, 'try_speech_recognition') as mock_recognize:
            mock_recognize.return_value = {"transcript": "Test message"}
            
            result = service.process_audio_immediate(b"x" * 200)
            
            assert "transcript" in result
            assert result["transcript"] == "Test message"
            mock_recognize.assert_called_once()

    def test_text_to_speech_fast_with_mock_client(self):
        """Test text_to_speech_fast with mocked client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"fast_audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        
        service = VoiceAssistantService(tts_client=mock_client)
        
        result = service.text_to_speech_fast("Hello world")
        
        assert result == b"fast_audio_data"
        mock_client.synthesize_speech.assert_called_once()

    def test_continuous_mode_parameter_support(self):
        """Test that _process_transcript method supports continuous_mode parameter."""
        import inspect
        from app.voice_assistant import VoiceAssistant
        
        voice_assistant = VoiceAssistant()
        
        # Check method signature
        sig = inspect.signature(voice_assistant._process_transcript)
        assert 'continuous_mode' in sig.parameters
        
        # Check default value
        continuous_param = sig.parameters['continuous_mode']
        assert continuous_param.default is False

    def test_voice_assistant_service_initialization(self):
        """Test that VoiceAssistantService initializes with new methods."""
        service = VoiceAssistantService()
        
        # Check that all required methods exist
        required_methods = [
            'process_audio_immediate',
            'text_to_speech_fast',
            'process_audio_chunk',
            'text_to_speech',
            'process_with_langchain'
        ]
        
        for method_name in required_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(service, method_name)), f"Method not callable: {method_name}"

    def test_voice_assistant_initialization(self):
        """Test that VoiceAssistant initializes with service containing new methods."""
        assistant = VoiceAssistant()
        
        # Check that service is initialized
        assert hasattr(assistant, 'service')
        assert isinstance(assistant.service, VoiceAssistantService)
        
        # Check that service has new methods
        assert hasattr(assistant.service, 'process_audio_immediate')
        assert hasattr(assistant.service, 'text_to_speech_fast')

    def test_continuous_mode_audio_processing_flow(self):
        """Test the complete continuous mode audio processing flow."""
        # This test simulates what happens when continuous_mode=True
        service = VoiceAssistantService()
        
        # Mock the speech client
        mock_client = Mock()
        service.speech_client = mock_client
        
        # Mock try_speech_recognition
        with patch.object(service, 'try_speech_recognition') as mock_recognize:
            mock_recognize.return_value = {"transcript": "Create a task"}
            
            # Test continuous mode flow
            audio_data = b"x" * 200
            result = service.process_audio_immediate(audio_data)
            
            # Verify immediate processing
            assert "transcript" in result
            assert result["transcript"] == "Create a task"
            
            # Verify recognition was called without cache (continuous mode)
            mock_recognize.assert_called_once_with(audio_data, use_cache=False)

    def test_fast_tts_vs_regular_tts_configuration(self):
        """Test that fast TTS uses different configuration than regular TTS."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        
        service = VoiceAssistantService(tts_client=mock_client)
        
        # Test both methods
        service.text_to_speech_fast("Test message")
        service.text_to_speech("Test message")
        
        # Verify both were called
        assert mock_client.synthesize_speech.call_count == 2
        
        # Get the call arguments
        calls = mock_client.synthesize_speech.call_args_list
        fast_call = calls[0]
        regular_call = calls[1]
        
        # Verify different voice settings
        fast_voice = fast_call[1]['voice']
        regular_voice = regular_call[1]['voice']
        
        # Fast should use Standard voice, regular should use Wavenet
        assert "Standard" in fast_voice.name
        assert "Wavenet" in regular_voice.name

    def test_backward_compatibility(self):
        """Test that existing functionality still works with new features."""
        service = VoiceAssistantService()
        
        # Test that old methods still exist and work
        assert hasattr(service, 'process_audio_chunk')
        assert hasattr(service, 'text_to_speech')
        assert hasattr(service, 'add_audio_chunk')
        assert hasattr(service, 'force_process_audio')
        
        # Test that new methods exist alongside old ones
        assert hasattr(service, 'process_audio_immediate')
        assert hasattr(service, 'text_to_speech_fast')
        
        # All methods should be callable
        for method_name in ['process_audio_chunk', 'text_to_speech', 'process_audio_immediate', 'text_to_speech_fast']:
            assert callable(getattr(service, method_name))
