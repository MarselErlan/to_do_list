"""
Scenario-based TDD tests for Voice Assistant.
These tests focus on realistic user scenarios and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
import base64
from app.voice_assistant import VoiceAssistant, VoiceAssistantService


class TestVoiceAssistantRealScenarios:
    """Test realistic voice assistant scenarios."""

    @pytest.fixture
    def voice_assistant(self):
        return VoiceAssistant()

    @pytest.fixture
    def mock_service(self):
        """Mock VoiceAssistantService for testing."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            yield mock_service

    def test_scenario_quick_task_creation(self, voice_assistant, mock_service):
        """
        SCENARIO: User quickly says 'Call mom at 3pm' and expects immediate task creation.
        EXPECTED: Task created successfully with confirmation audio.
        """
        # Given: User provides clear, complete voice command
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
        
        mock_service.text_to_speech.return_value = b"task_created_confirmation"
        
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

    def test_scenario_unclear_request_needs_clarification(self, voice_assistant, mock_service):
        """
        SCENARIO: User says 'I need to call someone' (unclear who).
        EXPECTED: System asks for clarification politely.
        """
        # Given: User provides unclear voice command
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
        
        # When: Processing the unclear command
        result = voice_assistant.process_voice_command(
            audio_data=b"unclear_audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should ask for clarification
        assert result["task_created"] is False
        assert result["clarification_needed"] is True
        assert "Who would you like to call" in result["llm_result"]["response"]

    def test_scenario_complex_meeting_scheduling(self, voice_assistant, mock_service):
        """
        SCENARIO: User schedules complex meeting with multiple attendees.
        EXPECTED: System handles complexity and creates detailed task.
        """
        # Given: User provides complex meeting request
        complex_request = "Schedule a team meeting tomorrow at 2 PM with John, Sarah, and Mike to discuss the quarterly roadmap and budget allocation"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": complex_request,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Team meeting - quarterly roadmap & budget",
            "start_time": "14:00:00",
            "start_date": "2025-01-16",
            "attendees": ["John", "Sarah", "Mike"],
            "response": "Meeting scheduled: Team meeting tomorrow at 2:00 PM with John, Sarah, and Mike for quarterly roadmap and budget allocation"
        }
        
        mock_service.text_to_speech.return_value = b"meeting_scheduled_audio"
        
        # When: Processing the complex command
        result = voice_assistant.process_voice_command(
            audio_data=b"complex_audio_input",
            user_id=1,
            session_name="Work"
        )
        
        # Then: System should handle complexity successfully
        assert result["task_created"] is True
        assert "quarterly roadmap" in result["task_title"]
        assert "audio_response" in result

    def test_scenario_noisy_environment_processing(self, voice_assistant, mock_service):
        """
        SCENARIO: User speaks in noisy environment with background sounds.
        EXPECTED: System filters noise and processes core request.
        """
        # Given: User speaks with background noise
        noisy_transcript = "I need to... um... call my mom at... let me see... 3pm today"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": noisy_transcript,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "Task created: Call mom at 3:00 PM today"
        }
        
        mock_service.text_to_speech.return_value = b"task_created_despite_noise"
        
        # When: Processing noisy input
        result = voice_assistant.process_voice_command(
            audio_data=b"noisy_audio_input",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should extract core intent
        assert result["task_created"] is True
        assert result["transcript"] == noisy_transcript
        assert result["task_title"] == "Call mom"

    def test_scenario_multiple_tasks_in_one_request(self, voice_assistant, mock_service):
        """
        SCENARIO: User tries to create multiple tasks in one voice command.
        EXPECTED: System handles gracefully (creates first task, asks about second).
        """
        # Given: User provides multiple tasks
        multi_task_request = "Call mom at 3pm today and email the boss about the report and schedule dentist appointment"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": multi_task_request,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "response": "I created a task to call mom at 3:00 PM today. Would you like me to help with the email to your boss as well?"
        }
        
        mock_service.text_to_speech.return_value = b"first_task_created_audio"
        
        # When: Processing multi-task request
        result = voice_assistant.process_voice_command(
            audio_data=b"multi_task_audio",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should handle first task and offer to help with others
        assert result["task_created"] is True
        assert result["task_title"] == "Call mom"
        assert "audio_response" in result

    def test_scenario_service_unavailable_graceful_fallback(self, voice_assistant, mock_service):
        """
        SCENARIO: Google Cloud services are temporarily unavailable.
        EXPECTED: System provides helpful error message and fallback.
        """
        # Given: Google Cloud services are down
        mock_service.process_audio_chunk.side_effect = Exception("Google Cloud Speech API unavailable")
        
        # When: Processing voice command during outage
        result = voice_assistant.process_voice_command(
            audio_data=b"audio_during_outage",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should provide helpful error message
        assert "error" in result
        assert "Google Cloud Speech API unavailable" in result["error"]

    def test_scenario_user_speaks_too_fast(self, voice_assistant, mock_service):
        """
        SCENARIO: User speaks very quickly, transcript may be incomplete.
        EXPECTED: System asks user to speak more slowly or repeat.
        """
        # Given: User speaks too quickly
        fast_transcript = "callmomthreepmtodayalsoschedulemeetingwithteam"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": fast_transcript,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": False,
            "error": "Unable to parse request clearly",
            "response": "I didn't catch that clearly. Could you please speak a bit more slowly and repeat your request?"
        }
        
        mock_service.text_to_speech.return_value = b"speak_slower_audio"
        
        # When: Processing fast speech
        result = voice_assistant.process_voice_command(
            audio_data=b"fast_speech_audio",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should ask user to slow down
        assert result["task_created"] is False
        assert result["clarification_needed"] is True
        assert "speak a bit more slowly" in result["llm_result"]["response"]

    def test_scenario_user_interrupts_themselves(self, voice_assistant, mock_service):
        """
        SCENARIO: User starts speaking, stops, then starts again.
        EXPECTED: System handles interruption gracefully.
        """
        # Given: User interrupts themselves
        interrupted_transcript = "I need to call... wait, no, I need to email John about the meeting"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": interrupted_transcript,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Email John about meeting",
            "response": "Task created: Email John about the meeting"
        }
        
        mock_service.text_to_speech.return_value = b"email_task_created"
        
        # When: Processing interrupted speech
        result = voice_assistant.process_voice_command(
            audio_data=b"interrupted_audio",
            user_id=1,
            session_name="Work"
        )
        
        # Then: System should process final intent
        assert result["task_created"] is True
        assert result["task_title"] == "Email John about meeting"

    def test_scenario_time_zone_awareness(self, voice_assistant, mock_service):
        """
        SCENARIO: User mentions time without specifying timezone.
        EXPECTED: System uses user's timezone or asks for clarification.
        """
        # Given: User mentions time without timezone
        mock_service.process_audio_chunk.return_value = {
            "transcript": "Call mom at 3pm",
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Call mom",
            "start_time": "15:00:00",
            "start_date": "2025-01-15",
            "timezone": "America/New_York",  # User's timezone
            "response": "Task created: Call mom at 3:00 PM EST today"
        }
        
        mock_service.text_to_speech.return_value = b"timezone_aware_response"
        
        # When: Processing time-based request
        result = voice_assistant.process_voice_command(
            audio_data=b"time_request_audio",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should use appropriate timezone
        assert result["task_created"] is True
        assert result["task_title"] == "Call mom"

    def test_scenario_privacy_sensitive_task(self, voice_assistant, mock_service):
        """
        SCENARIO: User creates privacy-sensitive task.
        EXPECTED: System handles appropriately based on privacy settings.
        """
        # Given: User creates sensitive task
        sensitive_request = "Schedule doctor appointment for confidential health matter"
        
        mock_service.process_audio_chunk.return_value = {
            "transcript": sensitive_request,
            "is_final": True
        }
        
        mock_service.process_with_langchain.return_value = {
            "is_complete": True,
            "task_title": "Doctor appointment",
            "is_private": True,
            "response": "Private task created: Doctor appointment (details kept confidential)"
        }
        
        mock_service.text_to_speech.return_value = b"private_task_created"
        
        # When: Processing sensitive request
        result = voice_assistant.process_voice_command(
            audio_data=b"sensitive_audio",
            user_id=1,
            session_name="Personal"
        )
        
        # Then: System should handle privacy appropriately
        assert result["task_created"] is True
        assert result["task_title"] == "Doctor appointment"
        assert "audio_response" in result


class TestVoiceAssistantErrorScenarios:
    """Test error scenarios and edge cases."""

    @pytest.fixture
    def voice_assistant(self):
        return VoiceAssistant()

    def test_network_connectivity_issues(self, voice_assistant):
        """Test handling of network connectivity issues."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Simulate network error
            mock_service.process_audio_chunk.side_effect = Exception("Network unreachable")
            
            result = voice_assistant.process_voice_command(
                audio_data=b"audio_data",
                user_id=1,
                session_name="Personal"
            )
            
            assert "error" in result
            assert "Network unreachable" in result["error"]

    def test_invalid_user_session(self, voice_assistant):
        """Test handling of invalid user sessions."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Test message",
                "is_final": True
            }
            
            # Simulate invalid session
            mock_service.process_with_langchain.side_effect = Exception("Invalid session")
            
            result = voice_assistant.process_voice_command(
                audio_data=b"audio_data",
                user_id=999,  # Invalid user
                session_name="NonExistent"
            )
            
            assert "error" in result
            assert "Invalid session" in result["error"]

    def test_audio_format_not_supported(self, voice_assistant):
        """Test handling of unsupported audio formats."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Simulate unsupported audio format
            mock_service.process_audio_chunk.return_value = {
                "error": "Unsupported audio format: MP3"
            }
            
            result = voice_assistant.process_voice_command(
                audio_data=b"mp3_audio_data",
                user_id=1,
                session_name="Personal"
            )
            
            assert "error" in result
            assert "Unsupported audio format" in result["error"]


class TestVoiceAssistantPerformanceScenarios:
    """Test performance-related scenarios."""

    @pytest.fixture
    def voice_assistant(self):
        return VoiceAssistant()

    def test_high_load_performance(self, voice_assistant):
        """Test system performance under high load."""
        import time
        
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock fast responses
            mock_service.process_audio_chunk.return_value = {
                "transcript": "Quick task",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created"
            }
            
            mock_service.text_to_speech.return_value = b"audio"
            
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
            assert all(result["task_created"] for result in results)
            
            # Should complete within reasonable time
            total_time = end_time - start_time
            assert total_time < 10.0, f"High load test took {total_time:.2f}s"

    def test_large_audio_file_handling(self, voice_assistant):
        """Test handling of large audio files."""
        with patch('app.voice_assistant.VoiceAssistantService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock processing of large audio file
            mock_service.process_audio_chunk.return_value = {
                "transcript": "This is a very long transcript from a large audio file",
                "is_final": True
            }
            
            mock_service.process_with_langchain.return_value = {
                "is_complete": True,
                "response": "Task created from large audio file"
            }
            
            mock_service.text_to_speech.return_value = b"large_response_audio"
            
            # Simulate large audio file (10MB)
            large_audio = b"0" * (10 * 1024 * 1024)
            
            result = voice_assistant.process_voice_command(
                audio_data=large_audio,
                user_id=1,
                session_name="Test"
            )
            
            assert result["task_created"] is True
            assert "large audio file" in result["task_title"] 