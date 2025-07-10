"""
WebSocket Tests for Continuous Voice Chat
Tests the WebSocket endpoint functionality for continuous voice mode.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from app.main import app
from app.voice_assistant import VoiceAssistant


class TestContinuousVoiceWebSocket:
    """Test WebSocket functionality for continuous voice chat."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"
        return websocket

    @pytest.fixture
    def voice_assistant(self):
        """Create a voice assistant instance for testing."""
        return VoiceAssistant()

    @pytest.fixture
    def sample_audio_base64(self):
        """Sample base64 encoded audio for testing."""
        return base64.b64encode(b"sample_audio_data_16khz").decode()

    @pytest.mark.asyncio
    async def test_websocket_continuous_mode_message(self, voice_assistant, mock_websocket, sample_audio_base64):
        """Test WebSocket handling of continuous mode messages."""
        # Setup continuous mode message
        message = json.dumps({
            "audio": sample_audio_base64,
            "continuous_mode": True
        })
        
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        # Mock the voice processing
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"transcript": "Create a test task"}
            
            with patch.object(voice_assistant, '_process_transcript') as mock_process:
                mock_process.return_value = None
                
                with patch('app.voice_assistant.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                    mock_get_db.return_value = mock_db
                    
                    # Execute
                    await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify immediate processing was called
        mock_immediate.assert_called_once()
        audio_data = mock_immediate.call_args[0][0]
        assert isinstance(audio_data, bytes)
        
        # Verify transcript processing was called with continuous mode
        mock_process.assert_called_once()
        call_args = mock_process.call_args[0]
        continuous_mode_arg = call_args[5]  # 6th positional argument
        assert continuous_mode_arg is True

    @pytest.mark.asyncio
    async def test_websocket_interrupt_action(self, voice_assistant, mock_websocket):
        """Test WebSocket interrupt action handling."""
        # Setup interrupt message
        interrupt_message = json.dumps({"action": "interrupt"})
        
        mock_websocket.receive_text.side_effect = [interrupt_message, WebSocketDisconnect()]
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify interrupt response was sent
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["status"] == "interrupted"
        assert "listening" in response["message"].lower()

    @pytest.mark.asyncio
    async def test_websocket_session_update(self, voice_assistant, mock_websocket):
        """Test WebSocket session update handling."""
        # Setup session update message
        session_message = json.dumps({"session_name": "Work Projects"})
        
        mock_websocket.receive_text.side_effect = [session_message, WebSocketDisconnect()]
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify session update response was sent
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert response["status"] == "session_updated"
        assert response["session_name"] == "Work Projects"

    @pytest.mark.asyncio
    async def test_websocket_malformed_message(self, voice_assistant, mock_websocket):
        """Test WebSocket handling of malformed messages."""
        # Setup malformed message
        malformed_message = "not valid json"
        
        mock_websocket.receive_text.side_effect = [malformed_message, WebSocketDisconnect()]
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify error response was sent
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert "error" in response
        assert "json" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_websocket_empty_audio_data(self, voice_assistant, mock_websocket):
        """Test WebSocket handling of empty audio data."""
        # Setup message with empty audio
        message = json.dumps({
            "audio": "",
            "continuous_mode": True
        })
        
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify error response was sent
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert "error" in response
        assert "audio" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_websocket_audio_processing_error(self, voice_assistant, mock_websocket, sample_audio_base64):
        """Test WebSocket handling of audio processing errors."""
        # Setup message
        message = json.dumps({
            "audio": sample_audio_base64,
            "continuous_mode": True
        })
        
        mock_websocket.receive_text.side_effect = [message, WebSocketDisconnect()]
        
        # Mock processing to fail
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"error": "Audio processing failed"}
            
            with patch('app.voice_assistant.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                mock_get_db.return_value = mock_db
                
                # Execute
                await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify error response was sent
        mock_websocket.send_json.assert_called_once()
        response = mock_websocket.send_json.call_args[0][0]
        assert "error" in response
        assert "Audio processing failed" in response["error"]

    @pytest.mark.asyncio
    async def test_websocket_connection_close(self, voice_assistant, mock_websocket):
        """Test WebSocket connection closing gracefully."""
        # Setup immediate disconnect
        mock_websocket.receive_text.side_effect = [WebSocketDisconnect()]
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Execute - should not raise exception
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify connection was accepted
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_multiple_messages(self, voice_assistant, mock_websocket, sample_audio_base64):
        """Test WebSocket handling of multiple messages in sequence."""
        # Setup multiple messages
        messages = [
            json.dumps({"audio": sample_audio_base64, "continuous_mode": True}),
            json.dumps({"action": "interrupt"}),
            json.dumps({"audio": sample_audio_base64, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"transcript": "Test message"}
            
            with patch.object(voice_assistant, '_process_transcript') as mock_process:
                mock_process.return_value = None
                
                with patch('app.voice_assistant.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                    mock_get_db.return_value = mock_db
                    
                    # Execute
                    await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify all messages were processed
        assert mock_immediate.call_count == 2  # Two audio messages
        assert mock_process.call_count == 2    # Two transcript processing calls
        assert mock_websocket.send_json.call_count >= 3  # At least 3 responses

    def test_websocket_message_parsing(self):
        """Test WebSocket message parsing utilities."""
        # Test valid JSON parsing
        valid_message = '{"audio": "dGVzdA==", "continuous_mode": true}'
        
        try:
            parsed = json.loads(valid_message)
            assert "audio" in parsed
            assert parsed["continuous_mode"] is True
        except json.JSONDecodeError:
            pytest.fail("Valid JSON should parse successfully")
        
        # Test invalid JSON
        invalid_message = '{"audio": "test", "continuous_mode": true'  # Missing closing brace
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_message)

    def test_audio_data_validation(self):
        """Test audio data validation for WebSocket messages."""
        # Test valid base64 audio
        valid_audio = base64.b64encode(b"test_audio_data").decode()
        
        try:
            decoded = base64.b64decode(valid_audio)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Valid base64 should decode successfully")
        
        # Test invalid base64
        invalid_audio = "not_base64_data!"
        
        with pytest.raises(Exception):
            base64.b64decode(invalid_audio)

    @pytest.mark.asyncio
    async def test_websocket_performance(self, voice_assistant, mock_websocket, sample_audio_base64):
        """Test WebSocket performance with continuous mode."""
        # Setup rapid message sequence
        messages = [
            json.dumps({"audio": sample_audio_base64, "continuous_mode": True})
            for _ in range(5)
        ] + [WebSocketDisconnect()]
        
        mock_websocket.receive_text.side_effect = messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"transcript": "Fast processing"}
            
            with patch.object(voice_assistant, '_process_transcript') as mock_process:
                mock_process.return_value = None
                
                with patch('app.voice_assistant.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                    mock_get_db.return_value = mock_db
                    
                    import time
                    start_time = time.time()
                    
                    # Execute
                    await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
        
        # Verify all messages were processed
        assert mock_immediate.call_count == 5
        assert mock_process.call_count == 5
        
        # Performance check - should handle 5 messages reasonably quickly
        assert processing_time < 2.0  # Should complete within 2 seconds
        print(f"Processed 5 continuous messages in {processing_time:.3f} seconds")
