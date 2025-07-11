
import pytest
from unittest.mock import Mock, patch
from app.voice_assistant import VoiceAssistant


class TestVoiceAssistantRealScenarios:
    """Test realistic voice assistant scenarios."""

    @pytest.fixture
    def voice_assistant(self):
        """Fixture to provide a VoiceAssistant instance with a mocked service."""
        va = VoiceAssistant()
        # Mock the service to avoid actual API calls
        va.service = Mock()
        return va

    def test_scenario_quick_task_creation(self, voice_assistant):
        # ... (rest of the test remains the same)
        # Given: User provides clear, complete voice command
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": "Call mom at 3pm today",
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "Task created: Call mom at 3:00 PM today"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"task_created_confirmation"
        
        # When: Processing the voice command
        result = voice_assistant.process_voice_command(
            audio_data=b"clear_audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: Task should be created successfully
        assert result["task_created"] is True
        assert result["transcript"] == "Call mom at 3pm today"
        assert result["task_title"] == "Call mom"
        assert "audio_response" in result

    def test_scenario_unclear_request_needs_clarification(self, voice_assistant):
        # ...
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": "I need to call someone",
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": False,
            "clarification_needed": True,
            "response": "I'd be happy to help you make a call. Who would you like to call?"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"clarification_audio"
        
        # When: Processing the unclear command
        result = voice_assistant.process_voice_command(
            audio_data=b"unclear_audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should ask for clarification
        assert result["task_created"] is False
        assert result["clarification_needed"] is True
        assert "Who would you like to call" in result["response"]
    
    # (Apply similar changes to all other tests in this class)
    def test_scenario_complex_meeting_scheduling(self, voice_assistant):
        complex_request = "Schedule a team meeting tomorrow at 2 PM with John, Sarah, and Mike to discuss the quarterly roadmap and budget allocation"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": complex_request,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Team meeting - quarterly roadmap & budget",
            "start_time": "14:00:00",
            "start_date": "2025-01-16",
            "attendees": ["John", "Sarah", "Mike"],
            "response": "Meeting scheduled: Team meeting tomorrow at 2:00 PM with John, Sarah, and Mike for quarterly roadmap and budget allocation"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"meeting_scheduled_audio"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"complex_audio_input",
            user_id=1,
            session_name="Work"
        )
        
        assert result["task_created"] is True
        assert "quarterly roadmap" in result["task_title"]
        assert "audio_response" in result

    def test_scenario_noisy_environment_processing(self, voice_assistant):
        noisy_transcript = "I need to... um... call my mom at... let me see... 3pm today"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": noisy_transcript,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "Task created: Call mom at 3:00 PM today"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"task_created_despite_noise"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"noisy_audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        assert result["task_created"] is True
        assert result["transcript"] == noisy_transcript
        assert result["task_title"] == "Call mom"

    def test_scenario_multiple_tasks_in_one_request(self, voice_assistant):
        multi_task_request = "Call mom at 3pm today and email the boss about the report and schedule dentist appointment"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": multi_task_request,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "I created a task to call mom at 3:00 PM today. Would you like me to help with the email to your boss as well?"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"first_task_created_audio"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"multi_task_audio",
            user_id=1,
            session_name="Personal"
        )
        
        assert result["task_created"] is True
        assert result["task_title"] == "Call mom"
        assert "audio_response" in result

    def test_scenario_service_unavailable_graceful_fallback(self, voice_assistant):
        voice_assistant.service.process_audio_chunk.side_effect = Exception("Google Cloud Speech API unavailable")
        
        result = voice_assistant.process_voice_command(
            audio_data=b"audio_during_outage",
            user_id=1,
            session_name="Personal"
        )
        
        assert "error" in result
        assert "Google Cloud Speech API unavailable" in result["error"]

    def test_scenario_user_speaks_too_fast(self, voice_assistant):
        fast_transcript = "callmomthreepmtodayalsoschedulemeetingwithteam"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": fast_transcript,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": False,
            "clarification_needed": True,
            "response": "I didn't catch that clearly. Could you please speak a bit more slowly and repeat your request?"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"speak_slower_audio"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"fast_speech_audio",
            user_id=1,
            session_name="Personal"
        )
        
        assert result["task_created"] is False
        assert result["clarification_needed"] is True
        assert "speak a bit more slowly" in result["response"]

    def test_scenario_user_interrupts_themselves(self, voice_assistant):
        interrupted_transcript = "I need to call... wait, no, I need to email John about the meeting"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": interrupted_transcript,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Email John about meeting",
            "response": "Task created: Email John about the meeting"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"email_task_created"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"interrupted_audio",
            user_id=1,
            session_name="Work"
        )
        
        assert result["task_created"] is True
        assert result["task_title"] == "Email John about meeting"

    def test_scenario_time_zone_awareness(self, voice_assistant):
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": "Call mom at 3pm",
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "timezone": "America/New_York",
            "response": "Task created: Call mom at 3:00 PM EST today"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"timezone_aware_response"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"time_request_audio",
            user_id=1,
            session_name="Personal"
        )
        
        assert result["task_created"] is True
        assert result["task_title"] == "Call mom"

    def test_scenario_privacy_sensitive_task(self, voice_assistant):
        sensitive_request = "Schedule doctor appointment for confidential health matter"
        
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": sensitive_request,
            "is_final": True
        }
        
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Doctor appointment",
            "is_private": True,
            "response": "Private task created: Doctor appointment (details kept confidential)"
        }
        
        voice_assistant.service.text_to_speech.return_value = b"private_task_created"
        
        result = voice_assistant.process_voice_command(
            audio_data=b"sensitive_audio",
            user_id=1,
            session_name="Personal"
        )
        
        assert result["task_created"] is True
        assert result["task_title"] == "Doctor appointment"
        assert "audio_response" in result 


class TestVoiceAssistantErrorScenarios:
    """Test various error and edge case scenarios."""

    @pytest.fixture
    def voice_assistant(self):
        """Fixture to provide a VoiceAssistant instance with a mocked service."""
        va = VoiceAssistant()
        va.service = Mock()
        return va

    def test_network_connectivity_issues(self, voice_assistant):
        """SCENARIO: Network is down when trying to reach Google Cloud services."""
        voice_assistant.service.process_audio_chunk.side_effect = Exception("Network unreachable")

        result = voice_assistant.process_voice_command(
            audio_data=b"any_audio",
            user_id=1,
            session_name="Personal"
        )
        assert "error" in result
        assert "Network unreachable" in result["error"]

    def test_invalid_user_session(self, voice_assistant):
        """SCENARIO: User session is invalid or expired."""
        voice_assistant.service.process_audio_chunk.return_value = {"transcript": "test", "is_final": True}
        voice_assistant.service.process_with_langchain.side_effect = Exception("Invalid session")

        result = voice_assistant.process_voice_command(
            audio_data=b"any_audio",
            user_id=999,  # Invalid user
            session_name="Personal"
        )
        assert "error" in result
        assert "Invalid session" in result["error"]

    def test_audio_format_not_supported(self, voice_assistant):
        """SCENARIO: User provides audio in an unsupported format."""
        voice_assistant.service.process_audio_chunk.return_value = {"error": "Unsupported audio format"}

        result = voice_assistant.process_voice_command(
            audio_data=b"unsupported_format_audio",
            user_id=1,
            session_name="Personal"
        )
        assert "error" in result
        assert "Unsupported audio format" in result["error"]


class TestVoiceAssistantPerformanceScenarios:
    """Test system performance under various loads."""

    @pytest.fixture
    def voice_assistant(self):
        """Fixture to provide a VoiceAssistant instance with a mocked service."""
        va = VoiceAssistant()
        va.service = Mock()
        return va

    def test_high_load_performance(self, voice_assistant):
        """Test system performance under high load."""
        import time

        # Mock fast responses
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": "Quick task",
            "is_final": True
        }
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "response": "Task created"
        }
        voice_assistant.service.text_to_speech.return_value = b"audio"

        # Simulate high load
        start_time = time.time()
        results = []
        for i in range(20):
            result = voice_assistant.process_voice_command(
                audio_data=f"audio_{i}".encode(),
                user_id=1,
                session_name="Test"
            )
            results.append(result)
        end_time = time.time()

        # Verify performance and correctness
        assert len(results) == 20
        assert all(r["task_created"] for r in results)
        assert (end_time - start_time) < 5

    def test_large_audio_file_handling(self, voice_assistant):
        """Test handling of large audio files."""
        # Mock processing of large audio file
        voice_assistant.service.process_audio_chunk.return_value = {
            "transcript": "This is a very long transcript from a large audio file",
            "is_final": True
        }
        voice_assistant.service.process_with_langchain.return_value = {
            "task_created": True,
            "task_title": "Task from large audio file",
            "response": "Task created from large audio file"
        }
        voice_assistant.service.text_to_speech.return_value = b"large_response_audio"

        # Simulate large audio file
        large_audio = b"0" * (10 * 1024 * 1024)

        result = voice_assistant.process_voice_command(
            audio_data=large_audio,
            user_id=1,
            session_name="Test"
        )
        assert result["task_created"] is True
        assert "large audio file" in result["task_title"] 