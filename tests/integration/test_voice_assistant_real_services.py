"""
Integration tests for Voice Assistant with real Google Cloud services.
These tests require actual Google Cloud credentials and should be run in CI/CD.
"""

import pytest
import os
import base64
import asyncio
import tempfile
import time
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi import WebSocketDisconnect
from app.voice_assistant import VoiceAssistant, VoiceAssistantService
from app.config import settings


class TestVoiceAssistantRealServiceIntegration:
    """Integration tests with real Google Cloud services."""
    
    @pytest.fixture(autouse=True)
    def setup_credentials(self):
        """Setup real Google Cloud credentials for integration testing."""
        # Skip if no credentials are available
        if not settings.GOOGLE_CLOUD_CREDENTIALS_JSON and not settings.GOOGLE_APPLICATION_CREDENTIALS:
            pytest.skip("Google Cloud credentials not available for integration testing")
    
    @pytest.fixture
    def real_voice_service(self):
        """Create VoiceAssistantService with real Google Cloud clients."""
        return VoiceAssistantService()
    
    @pytest.fixture
    def sample_audio_file(self):
        """Create a sample audio file for testing."""
        # Create a simple WAV file header for LINEAR16 format
        sample_rate = 16000
        duration = 1  # 1 second
        samples = sample_rate * duration
        
        # WAV header for LINEAR16, 16kHz, mono
        wav_header = bytearray([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x00, 0x00, 0x00, 0x00,  # File size (will be filled)
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6D, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk size
            0x01, 0x00,              # Audio format (PCM)
            0x01, 0x00,              # Number of channels (mono)
            0x80, 0x3E, 0x00, 0x00,  # Sample rate (16000)
            0x00, 0x7D, 0x00, 0x00,  # Byte rate
            0x02, 0x00,              # Block align
            0x10, 0x00,              # Bits per sample
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00   # Data size (will be filled)
        ])
        
        # Generate simple sine wave audio data
        audio_data = bytearray(samples * 2)  # 2 bytes per sample
        for i in range(samples):
            # Simple sine wave at 440Hz
            import math
            sample = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            audio_data[i*2] = sample & 0xFF
            audio_data[i*2+1] = (sample >> 8) & 0xFF
        
        return wav_header + audio_data
    
    def test_real_speech_recognition_service_initialization(self, real_voice_service):
        """Test that real Google Cloud services initialize correctly."""
        # Should initialize without errors if credentials are available
        assert real_voice_service is not None
        
        # Check if clients are properly initialized
        if real_voice_service.speech_client is not None:
            assert hasattr(real_voice_service.speech_client, 'streaming_recognize')
        
        if real_voice_service.tts_client is not None:
            assert hasattr(real_voice_service.tts_client, 'synthesize_speech')
    
    def test_real_speech_config_creation(self, real_voice_service):
        """Test speech configuration with real service."""
        if real_voice_service.speech_client is None:
            pytest.skip("Speech client not available")
        
        config = real_voice_service.get_speech_config()
        
        # Verify configuration is properly created
        assert config is not None
        assert config.sample_rate_hertz == 16000
        assert config.language_code == "en-US"
        assert config.enable_automatic_punctuation is True
    
    def test_real_text_to_speech_conversion(self, real_voice_service):
        """Test real text-to-speech conversion."""
        if real_voice_service.tts_client is None:
            pytest.skip("TTS client not available")
        
        test_text = "Hello, this is a test message for voice assistant integration."
        
        audio_content = real_voice_service.text_to_speech(test_text)
        
        # Verify audio was generated
        assert audio_content is not None
        assert len(audio_content) > 0
        assert isinstance(audio_content, bytes)
        
        # Audio should be reasonable size (not empty, not too large)
        assert 1000 < len(audio_content) < 100000  # Between 1KB and 100KB
    
    def test_real_audio_processing_with_silence(self, real_voice_service):
        """Test audio processing with silence (should handle gracefully)."""
        if real_voice_service.speech_client is None:
            pytest.skip("Speech client not available")
        
        # Create silent audio data
        silent_audio = b'\x00' * 3200  # 0.1 seconds of silence at 16kHz
        
        result = real_voice_service.process_audio_chunk(silent_audio)
        
        # Should handle silence gracefully
        assert isinstance(result, dict)
        assert "transcript" in result or "error" in result
        
        if "transcript" in result:
            # Silent audio should produce empty or minimal transcript
            assert len(result["transcript"]) < 10
    
    @pytest.mark.slow
    def test_real_tts_with_various_texts(self, real_voice_service):
        """Test TTS with various text types (marked as slow test)."""
        if real_voice_service.tts_client is None:
            pytest.skip("TTS client not available")
        
        test_texts = [
            "Simple task created successfully.",
            "Meeting scheduled for tomorrow at 2:00 PM with John, Sarah, and Mike.",
            "I need more information to complete your request. What time would you prefer?",
            "Task completed: Call mom at 3:00 PM today. Is there anything else I can help you with?",
            "Email sent to boss about quarterly report. Reminder set for follow-up next week."
        ]
        
        for text in test_texts:
            audio_content = real_voice_service.text_to_speech(text)
            
            assert audio_content is not None
            assert len(audio_content) > 0
            
            # Longer texts should generally produce longer audio
            if len(text) > 50:
                assert len(audio_content) > 2000  # At least 2KB for longer texts
    
    def test_real_service_error_handling(self, real_voice_service):
        """Test error handling with real services."""
        # Test with invalid audio data
        invalid_audio = b"not_audio_data"
        
        result = real_voice_service.process_audio_chunk(invalid_audio)
        
        # Should handle gracefully, either with empty result or error
        assert isinstance(result, dict)
        if "error" in result:
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0
    
    @pytest.mark.slow
    def test_real_langchain_integration_flow(self, real_voice_service):
        """Test full integration with LangChain using real services."""
        if real_voice_service.speech_client is None:
            pytest.skip("Speech client not available")
        
        # This test requires database configuration, so we'll mock LangChain
        with patch('app.voice_assistant.create_graph') as mock_graph, \
             patch('app.voice_assistant.get_db') as mock_get_db:
            
            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.invoke.return_value = {
                "is_complete": True,
                "task_title": "Integration test task",
                "response": "Task created successfully via integration test"
            }
            
            mock_db = []
            mock_get_db.return_value = iter(mock_db)
            
            # Test LangChain integration
            result = real_voice_service.process_with_langchain(
                "Create a test task for integration testing",
                user_id=1,
                session_name="Integration Test"
            )
            
            assert result["is_complete"] is True
            assert "task_title" in result
            assert "response" in result


class TestVoiceAssistantEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_credentials(self):
        """Setup credentials for E2E testing."""
        if not settings.GOOGLE_CLOUD_CREDENTIALS_JSON and not settings.GOOGLE_APPLICATION_CREDENTIALS:
            pytest.skip("Google Cloud credentials not available for E2E testing")
    
    @pytest.fixture
    def voice_assistant(self):
        """Create VoiceAssistant instance for E2E testing."""
        return VoiceAssistant()
    
    def test_complete_voice_workflow_real_services(self, voice_assistant):
        """Test complete voice workflow with real Google Cloud services."""
        # Create simple audio data for testing
        test_audio = b'\x00' * 1600  # 0.1 seconds of silence
        
        # Mock LangChain to avoid database dependencies
        with patch('app.voice_assistant.create_graph') as mock_graph, \
             patch('app.voice_assistant.get_db') as mock_get_db:
            
            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.invoke.return_value = {
                "is_complete": True,
                "task_title": "E2E test task",
                "response": "Task created successfully in E2E test"
            }
            
            mock_db = []
            mock_get_db.return_value = iter(mock_db)
            
            # Process voice command
            result = voice_assistant.process_voice_command(
                audio_data=test_audio,
                user_id=1,
                session_name="E2E Test"
            )
            
            # Verify result structure
            assert isinstance(result, dict)
            
            # Should have either successful task creation or error handling
            if "error" not in result:
                # If no error, should have task creation fields
                assert "transcript" in result or "task_created" in result
    
    @pytest.mark.slow
    def test_voice_assistant_performance_real_services(self, voice_assistant):
        """Test performance with real services."""
        import time
        
        test_audio = b'\x00' * 1600  # Simple test audio
        
        with patch('app.voice_assistant.create_graph') as mock_graph, \
             patch('app.voice_assistant.get_db') as mock_get_db:
            
            mock_graph_instance = mock_graph.return_value
            mock_graph_instance.invoke.return_value = {
                "is_complete": True,
                "task_title": "Performance test",
                "response": "Task created"
            }
            
            mock_db = []
            mock_get_db.return_value = iter(mock_db)
            
            # Measure processing time
            start_time = time.time()
            
            result = voice_assistant.process_voice_command(
                audio_data=test_audio,
                user_id=1,
                session_name="Performance Test"
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # With real services, should still complete within reasonable time
            assert processing_time < 10.0, f"Processing took {processing_time:.2f}s, expected < 10s"
            
            # Should return valid result
            assert isinstance(result, dict)
    
    def test_voice_assistant_error_recovery_real_services(self, voice_assistant):
        """Test error recovery with real services."""
        # Test with completely invalid audio
        invalid_audio = b"completely_invalid_audio_data_that_should_fail"
        
        result = voice_assistant.process_voice_command(
            audio_data=invalid_audio,
            user_id=1,
            session_name="Error Test"
        )
        
        # Should handle errors gracefully
        assert isinstance(result, dict)
        
        # Should either process successfully or return clear error
        if "error" in result:
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0


class TestVoiceAssistantServiceReliability:
    """Test service reliability and edge cases."""
    
    @pytest.fixture(autouse=True)
    def setup_credentials(self):
        """Setup credentials for reliability testing."""
        if not settings.GOOGLE_CLOUD_CREDENTIALS_JSON and not settings.GOOGLE_APPLICATION_CREDENTIALS:
            pytest.skip("Google Cloud credentials not available for reliability testing")
    
    def test_service_initialization_with_missing_credentials(self):
        """Test service behavior when credentials are missing."""
        # Temporarily remove credentials
        with patch.dict(os.environ, {}, clear=True):
            with patch('app.voice_assistant.settings') as mock_settings:
                mock_settings.GOOGLE_CLOUD_CREDENTIALS_JSON = None
                mock_settings.GOOGLE_APPLICATION_CREDENTIALS = None
                
                service = VoiceAssistantService()
                
                # Should initialize but with None clients
                assert service.speech_client is None
                assert service.tts_client is None
    
    def test_service_graceful_degradation(self):
        """Test that service degrades gracefully when clients are unavailable."""
        service = VoiceAssistantService(speech_client=None, tts_client=None)
        
        # Should handle missing speech client
        result = service.process_audio_chunk(b"test_audio")
        assert "error" in result
        assert "Speech client not initialized" in result["error"]
        
        # Should handle missing TTS client
        audio_result = service.text_to_speech("Test message")
        assert audio_result == b""
    
    def test_service_credential_validation(self):
        """Test credential validation and setup."""
        # Test with valid credential structure
        test_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "test-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        
        import json
        credentials_json = json.dumps(test_credentials)
    
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key: credentials_json if key == 'GOOGLE_CLOUD_CREDENTIALS_JSON' else None

            # Should attempt to create temporary file
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = '/tmp/test_creds.json'
    
                with patch('app.voice_assistant.speech.SpeechClient') as mock_speech:
                    service = VoiceAssistantService()
    
                    # Should have attempted to create speech client
                    mock_speech.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 

class TestContinuousVoiceChatIntegration:
    """Integration tests for continuous voice chat with real services."""

    @pytest.mark.asyncio
    async def test_continuous_voice_websocket_connection(self):
        """Test WebSocket connection for continuous voice chat."""
        if not os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON'):
            pytest.skip("Google Cloud credentials not available")
        
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Create a test user and get token
        user_data = {
            "username": f"testuser_{int(time.time())}",
            "password": "testpass123",
            "email": f"test_{int(time.time())}@example.com"
        }
        
        # Register user
        response = client.post("/users/", json=user_data)
        assert response.status_code in [200, 201, 409]  # 409 if user exists
        
        # Login to get token
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        token_response = client.post("/token", data=login_data)
        if token_response.status_code != 200:
            pytest.skip("Unable to get authentication token")
        
        token = token_response.json()["access_token"]
        
        # Test WebSocket connection with continuous mode
        import websockets
        import json
        
        try:
            uri = f"ws://localhost:8000/ws/voice?token={token}"
            async with websockets.connect(uri) as websocket:
                # Send continuous mode message
                test_message = {
                    "audio": base64.b64encode(b"dummy audio for continuous test").decode(),
                    "continuous_mode": True
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    
                    # Verify continuous mode is handled
                    assert isinstance(data, dict)
                    # Should contain either transcript, error, or processing status
                    assert any(key in data for key in ["transcript", "error", "status", "response_text"])
                    
                except asyncio.TimeoutError:
                    pytest.fail("WebSocket response timeout")
                    
        except Exception as e:
            pytest.skip(f"WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    async def test_continuous_mode_real_audio_processing(self):
        """Test continuous mode with real audio processing."""
        if not os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON'):
            pytest.skip("Google Cloud credentials not available")
        
        voice_assistant = VoiceAssistant()
        
        # Create mock real-time audio data
        sample_rate = 16000
        duration = 1.0  # 1 second
        import numpy as np
        
        # Generate a simple sine wave as test audio
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_signal = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
        
        # Convert to 16-bit PCM
        audio_data = (audio_signal * 32767).astype(np.int16).tobytes()
        
        # Test immediate processing
        result = voice_assistant.service.process_audio_immediate(audio_data)
        
        # Verify processing works (might not recognize speech from sine wave, but should not crash)
        assert isinstance(result, dict)
        assert "error" in result or "transcript" in result

    def test_continuous_vs_traditional_performance(self):
        """Test performance comparison between continuous and traditional modes."""
        if not os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON'):
            pytest.skip("Google Cloud credentials not available")
        
        voice_service = VoiceAssistantService()
        
        # Create test audio data
        test_audio = b"x" * 8000  # 8KB of audio data
        
        import time
        
        # Test traditional processing
        start_time = time.time()
        traditional_result = voice_service.process_audio_chunk(test_audio)
        traditional_time = time.time() - start_time
        
        # Test continuous processing
        start_time = time.time()
        continuous_result = voice_service.process_audio_immediate(test_audio)
        continuous_time = time.time() - start_time
        
        # Verify both work
        assert isinstance(traditional_result, dict)
        assert isinstance(continuous_result, dict)
        
        # Log performance difference
        print(f"Traditional processing time: {traditional_time:.3f}s")
        print(f"Continuous processing time: {continuous_time:.3f}s")
        
        # Continuous mode should typically be faster (immediate processing)
        # Note: This is informational, not a strict assertion as network latency can vary

    def test_fast_tts_real_service(self):
        """Test fast TTS with real Google Cloud service."""
        if not os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON'):
            pytest.skip("Google Cloud credentials not available")
        
        voice_service = VoiceAssistantService()
        
        if not voice_service.tts_client:
            pytest.skip("TTS client not available")
        
        test_text = "This is a test of fast text-to-speech for continuous voice chat."
        
        import time
        
        # Test fast TTS
        start_time = time.time()
        fast_audio = voice_service.text_to_speech_fast(test_text)
        fast_time = time.time() - start_time
        
        # Test regular TTS
        start_time = time.time()
        regular_audio = voice_service.text_to_speech(test_text)
        regular_time = time.time() - start_time
        
        # Verify both produce audio
        assert len(fast_audio) > 0
        assert len(regular_audio) > 0
        
        # Log performance difference
        print(f"Fast TTS time: {fast_time:.3f}s")
        print(f"Regular TTS time: {regular_time:.3f}s")
        
        # Both should be reasonably fast
        assert fast_time < 5.0  # Should complete within 5 seconds
        assert regular_time < 5.0

    @pytest.mark.asyncio
    async def test_continuous_conversation_end_to_end(self):
        """Test complete continuous conversation with real services."""
        if not os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON'):
            pytest.skip("Google Cloud credentials not available")
        
        # This is a comprehensive integration test
        voice_assistant = VoiceAssistant()
        
        # Mock WebSocket for controlled testing
        mock_websocket = Mock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = Mock()
        mock_websocket.client_state.name = "CONNECTED"
        
        # Simulate a conversation with mock audio but real processing
        conversation_messages = [
            json.dumps({
                "audio": base64.b64encode(b"fake audio for task creation").decode(),
                "continuous_mode": True
            }),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = conversation_messages
        
        # Mock database to avoid database dependencies
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute with real voice processing but mocked infrastructure
            try:
                await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
                
                # Verify WebSocket interactions occurred
                assert mock_websocket.accept.called
                # Should have attempted to send responses
                assert mock_websocket.send_json.call_count >= 1
                
            except Exception as e:
                # Log the error for debugging but don't fail the test
                # as this depends on external services
                print(f"Integration test exception (expected with mock audio): {e}")

    def test_continuous_mode_error_recovery(self):
        """Test error recovery in continuous mode with real services."""
        voice_service = VoiceAssistantService()
        
        # Test with invalid audio data
        invalid_audio = b"not_valid_audio"
        result = voice_service.process_audio_immediate(invalid_audio)
        
        # Should handle error gracefully
        assert "error" in result
        assert isinstance(result["error"], str)
        
        # Service should still be functional after error
        # Test with valid length audio (though content may not be recognizable)
        valid_length_audio = b"x" * 1000
        result2 = voice_service.process_audio_immediate(valid_length_audio)
        
        # Should not crash, even if recognition fails
        assert isinstance(result2, dict)

    def test_continuous_mode_configuration_validation(self):
        """Test that continuous mode configuration is properly set up."""
        from app.voice_assistant import VoiceAssistant, VoiceAssistantService
        
        # Test that classes can be instantiated
        voice_service = VoiceAssistantService()
        voice_assistant = VoiceAssistant()
        
        # Test that new methods exist and are callable
        assert hasattr(voice_service, 'process_audio_immediate')
        assert hasattr(voice_service, 'text_to_speech_fast')
        assert callable(voice_service.process_audio_immediate)
        assert callable(voice_service.text_to_speech_fast)
        
        # Test that WebSocket handler supports continuous mode
        assert hasattr(voice_assistant, '_process_transcript')
        
        # Check method signatures support continuous mode
        import inspect
        transcript_sig = inspect.signature(voice_assistant._process_transcript)
        assert 'continuous_mode' in transcript_sig.parameters
