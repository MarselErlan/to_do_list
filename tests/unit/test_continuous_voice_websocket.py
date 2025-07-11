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


@pytest.fixture(scope="class")
def event_loop_instance(request):
    """Fixture for managing the event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.usefixtures("event_loop_instance")
class TestContinuousVoiceWebSocket:
    """Test continuous voice chat WebSocket functionality."""

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
        # Check keyword arguments for continuous_mode
        _, kwargs = mock_process.call_args
        assert kwargs.get("continuous_mode") is True

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
        assert "interrupted" in response["message"].lower()

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
        assert "audio processing failed" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_websocket_connection_close(self, voice_assistant, mock_websocket):
        """Test WebSocket connection is properly closed."""
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()
        
        with patch('app.voice_assistant.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_multiple_messages(self, voice_assistant, mock_websocket, sample_audio_base64):
        """Test handling of multiple consecutive messages."""
        messages = [
            json.dumps({"audio": sample_audio_base64, "continuous_mode": True}),
            json.dumps({"audio": sample_audio_base64, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"transcript": "ok"}
            
            with patch.object(voice_assistant, '_process_transcript') as mock_process:
                
                with patch('app.voice_assistant.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                    mock_get_db.return_value = mock_db
                    
                    await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        assert mock_immediate.call_count == 2
        assert mock_process.call_count == 2 