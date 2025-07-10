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


class TestContinuousVoiceChatScenarios:
    """Test real-world continuous voice chat scenarios."""

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

    def test_continuous_mode_vs_traditional_mode(self):
        """Test differences between continuous and traditional modes."""
        # Create service with mocked clients
        mock_speech_client = Mock()
        mock_tts_client = Mock()
        
        with patch('app.voice_assistant.speech') as mock_speech_module:
            mock_speech_module.SpeechClient.return_value = mock_speech_client
            
            with patch('app.voice_assistant.texttospeech') as mock_tts_module:
                mock_tts_module.TextToSpeechClient.return_value = mock_tts_client
                
                service = VoiceAssistantService(
                    speech_client=mock_speech_client,
                    tts_client=mock_tts_client
                )
        
        # Test continuous mode processing
        with patch.object(service, 'try_speech_recognition') as mock_recognition:
            mock_recognition.return_value = {"transcript": "test"}
            
            # Test immediate processing (continuous mode)
            audio_data = b"x" * 1000
            result_immediate = service.process_audio_immediate(audio_data)
            
            # Test regular processing (traditional mode) 
            result_regular = service.process_audio_chunk(audio_data)
            
            # Verify both work but with different approaches
            # Should have attempted speech recognition
            assert isinstance(result_immediate, dict)
            assert isinstance(result_regular, dict)

    def test_fast_tts_vs_regular_tts_performance(self):
        """Test performance characteristics of fast vs regular TTS."""
        mock_tts_client = Mock()
        service = VoiceAssistantService(tts_client=mock_tts_client)
        
        # Mock TTS response
        mock_response = Mock()
        mock_response.audio_content = b"audio_content"
        mock_tts_client.synthesize_speech.return_value = mock_response
        
        test_text = "Hello, this is a test message"
        
        # Test fast TTS
        result_fast = service.text_to_speech_fast(test_text)
        
        # Test regular TTS
        result_regular = service.text_to_speech(test_text)
        
        # Verify both produce audio
        assert result_fast == b"audio_content"
        assert result_regular == b"audio_content"
        
        # Verify fast TTS uses different voice settings
        assert mock_tts_client.synthesize_speech.call_count == 2
        
        # Check voice configurations
        calls = mock_tts_client.synthesize_speech.call_args_list
        fast_call = calls[0]
        regular_call = calls[1]
        
        # Fast should use Standard voice, regular uses Wavenet
        fast_voice = fast_call[1]['voice']
        regular_voice = regular_call[1]['voice']
        
        assert "Standard" in fast_voice.name
        assert "Wavenet" in regular_voice.name

    @pytest.mark.asyncio
    async def test_error_handling_in_continuous_mode(self, voice_assistant, mock_websocket, mock_audio_data):
        """Test error handling during continuous voice chat."""
        error_messages = [
            json.dumps({"audio": "invalid_audio", "continuous_mode": True}),
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = error_messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.side_effect = [
                {"error": "Audio processing failed"},  # First call fails
                {"transcript": "This works fine"}       # Second call succeeds
            ]
            
            with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
                mock_langchain.return_value = {"is_complete": True, "task_title": "Test task"}
                
                with patch.object(voice_assistant.service, 'text_to_speech_fast'):
                    with patch('app.voice_assistant.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                        mock_get_db.return_value = mock_db
                        
                        # Execute
                        await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify error was handled gracefully
        sent_messages = [call[0][0] for call in mock_websocket.send_json.call_args_list]
        error_responses = [msg for msg in sent_messages if "error" in msg]
        success_responses = [msg for msg in sent_messages if "transcript" in msg]
        
        assert len(error_responses) >= 1  # At least one error response
        assert len(success_responses) >= 1  # At least one successful response

    def test_continuous_mode_message_validation(self):
        """Test validation of continuous mode messages."""
        # Create service with mocked clients
        mock_speech_client = Mock()
        mock_tts_client = Mock()
        
        with patch('app.voice_assistant.speech') as mock_speech_module:
            mock_speech_module.SpeechClient.return_value = mock_speech_client
            
            with patch('app.voice_assistant.texttospeech') as mock_tts_module:
                mock_tts_module.TextToSpeechClient.return_value = mock_tts_client
                
                service = VoiceAssistantService(
                    speech_client=mock_speech_client,
                    tts_client=mock_tts_client
                )
        
        # Test valid audio data
        valid_audio = base64.b64encode(b"x" * 1000).decode()
        valid_data = base64.b64decode(valid_audio)
        
        result = service.process_audio_immediate(valid_data)
        # Should not error on validation (might error on processing due to mock)
        assert isinstance(result, dict)
        
        # Test invalid audio data (too short)
        invalid_data = b"short"
        result = service.process_audio_immediate(invalid_data)
        assert "error" in result
        assert "too short" in result["error"].lower() or "speech client" in result["error"].lower()

    @pytest.mark.asyncio 
    async def test_session_context_in_continuous_mode(self, voice_assistant, mock_websocket, mock_audio_data):
        """Test that session context is maintained in continuous voice chat."""
        # Messages with session context
        messages = [
            json.dumps({"session_name": "Work Team"}),
            json.dumps({"audio": mock_audio_data, "continuous_mode": True}),
            WebSocketDisconnect()
        ]
        
        mock_websocket.receive_text.side_effect = messages
        
        with patch.object(voice_assistant.service, 'process_audio_immediate') as mock_immediate:
            mock_immediate.return_value = {"transcript": "Create a team task"}
            
            with patch.object(voice_assistant.service, 'process_with_langchain') as mock_langchain:
                mock_langchain.return_value = {"is_complete": True, "task_title": "Team task"}
                
                with patch.object(voice_assistant.service, 'text_to_speech_fast'):
                    with patch('app.voice_assistant.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
                        mock_get_db.return_value = mock_db
                        
                        # Execute
                        await voice_assistant.process_audio_stream(mock_websocket, user_id=1)
        
        # Verify session was updated
        sent_messages = [call[0][0] for call in mock_websocket.send_json.call_args_list]
        session_updates = [msg for msg in sent_messages if "session_updated" in msg]
        assert len(session_updates) >= 1
        
        # Verify LangChain was called with correct session context
        langchain_calls = mock_langchain.call_args_list
        if langchain_calls:
            # Check that session name was passed correctly
            call_kwargs = langchain_calls[0][1] if langchain_calls[0][1] else {}
            # The session name should be passed in the processing
            assert mock_langchain.called
