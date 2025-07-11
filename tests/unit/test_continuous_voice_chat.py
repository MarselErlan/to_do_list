"""
Continuous Voice Chat Test Suite
Tests for ChatGPT-style continuous voice conversation functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import base64
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.voice_assistant import VoiceAssistant, VoiceAssistantService


@pytest.fixture(scope="class")
def event_loop_instance(request):
    """Fixture for managing the event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.usefixtures("event_loop_instance")
class TestContinuousVoiceChatScenarios:
    """Test scenarios for continuous voice chat."""

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket for testing."""
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
        """Voice assistant instance for testing."""
        return VoiceAssistant()

    @pytest.fixture
    def mock_audio_data(self):
        """Mock audio data for testing."""
        return base64.b64encode(b"mock_audio_16khz_linear16").decode()

    @pytest.mark.asyncio
    async def test_chatgpt_style_continuous_conversation(self, voice_assistant, mock_websocket, mock_audio_data):
        """Test ChatGPT-style continuous voice conversation flow."""
        # Simulate a natural conversation flow
        conversation_flow = [
            # User starts talking
            json.dumps({
                "audio": mock_audio_data,
                "continuous_mode": True
            }),
            # User interrupts while assistant is speaking
            json.dumps({
                "action": "interrupt"
            }),
            # User provides clarification
            json.dumps({
                "audio": mock_audio_data,
                "continuous_mode": True
            }),
            # End conversation
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = conversation_flow
        
        # Mock the processing pipeline
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.side_effect = [
                {"transcript": "Create a task"},
                {"transcript": "Create a task to call John at 3 PM tomorrow"}
            ]
            
            with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
                mock_langchain.side_effect = [
                    {
                        "is_complete": False,
                        "clarification_questions": ["What should the task be about?"]
                    },
                    {
                        "is_complete": True,
                        "task_title": "Call John at 3 PM tomorrow"
                    }
                ]
                
                with patch.object(voice_assistant.service, 'text_to_speech_fast') as mock_tts:
                    mock_tts.return_value = b"audio_response"
                    
                    with patch('app.voice_assistant.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                        mock_get_db.return_value = mock_db
                        
                        # Execute
                        await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify conversation flow
        assert mock_immediate.call_count == 2  # Two voice inputs processed
        assert mock_langchain.call_count == 2  # Two LangChain interactions
        
        # Verify interrupt was handled
        sent_messages = [call[0][0] for call in mock_websocket.send_json.call_args_list]
        interrupt_handled = any("interrupted" in msg.get("status", "") for msg in sent_messages)
        assert interrupt_handled

    @pytest.mark.asyncio
    async def test_voice_activity_detection_simulation(self, voice_assistant, mock_websocket, mock_audio_data):
        """Test simulated voice activity detection behavior."""
        # Simulate rapid voice activity detection
        voice_sequence = [
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = voice_sequence
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.side_effect = [
                {"transcript": "Create"},
                {"transcript": "Create a"},
                {"transcript": "Create a task to buy groceries"}
            ]
            
            with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
                mock_langchain.return_value = {
                    "is_complete": True,
                    "task_title": "Buy groceries"
                }
                
                with patch.object(voice_assistant.service, 'text_to_speech_fast'):
                    with patch('app.voice_assistant.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                        mock_get_db.return_value = mock_db
                        
                        # Execute
                        await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify all audio chunks were processed
        assert mock_immediate.call_count == 3
        assert mock_langchain.call_count == 3  # Each transcript processed

    @pytest.mark.asyncio
    async def test_interrupt_during_assistant_speech(self, voice_assistant, mock_websocket, mock_audio_data):
        """Test user interrupting assistant while it's speaking."""
        # Conversation with interruption
        messages = [
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            json.dumps({"action": "interrupt"}),  # User interrupts
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.side_effect = [
                {"transcript": "What's the weather?"},
                {"transcript": "Actually, create a task instead"}
            ]
            
            with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
                mock_langchain.side_effect = [
                    {"is_complete": False, "clarification_questions": ["I can help with tasks, not weather"]},
                    {"is_complete": True, "task_title": "Generic task"}
                ]
                
                with patch.object(voice_assistant.service, 'text_to_speech_fast'):
                    with patch('app.voice_assistant.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                        mock_get_db.return_value = mock_db
                        
                        # Execute
                        await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify interrupt was processed between audio messages
        sent_messages = [call[0][0] for call in mock_websocket.send_json.call_args_list]
        
        # Find interrupt response
        interrupt_response = None
        for msg in sent_messages:
            if msg.get("status") == "interrupted":
                interrupt_response = msg
                break
        
        assert interrupt_response is not None
        assert "interrupted" in interrupt_response["status"] 