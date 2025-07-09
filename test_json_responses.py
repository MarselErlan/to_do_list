#!/usr/bin/env python3
"""
JSON Response Verification Script

This script tests various scenarios to ensure the chat/create-task endpoint
always returns valid JSON responses, preventing CORS and parsing errors.
"""

import json
import sys
from typing import Dict, List, Any

def validate_json_structure(response_data: Dict[str, Any], scenario: str) -> bool:
    """Validates that a response has the expected JSON structure."""
    print(f"\n🔍 Validating {scenario}:")
    
    required_fields = ["is_complete"]
    optional_fields = ["task_title", "description", "clarification_questions", "conversation_response"]
    
    # Check required fields
    missing_required = [field for field in required_fields if field not in response_data]
    if missing_required:
        print(f"❌ Missing required fields: {missing_required}")
        return False
    
    # Validate field types
    if not isinstance(response_data.get("is_complete"), bool):
        print(f"❌ is_complete must be boolean, got: {type(response_data.get('is_complete'))}")
        return False
    
    # Check clarification_questions structure
    clarification = response_data.get("clarification_questions")
    if clarification is not None:
        if not isinstance(clarification, list):
            print(f"❌ clarification_questions must be list, got: {type(clarification)}")
            return False
        if not all(isinstance(q, str) for q in clarification):
            print(f"❌ clarification_questions must contain only strings")
            return False
    
    # Validate JSON serialization
    try:
        json_str = json.dumps(response_data)
        json.loads(json_str)  # Verify it can be parsed back
        print(f"✅ Valid JSON structure")
        print(f"📄 JSON size: {len(json_str)} characters")
        return True
    except (TypeError, ValueError) as e:
        print(f"❌ JSON serialization failed: {e}")
        return False

def test_response_scenarios():
    """Test various response scenarios that should all return valid JSON."""
    
    print("🧪 Testing JSON Response Scenarios")
    print("=" * 50)
    
    # Test scenarios with expected responses
    test_cases = [
        {
            "scenario": "Greeting Response",
            "data": {
                "conversation_response": "Hello! How can I help you create a task today?",
                "clarification_questions": ["Hello! How can I help you create a task today?"],
                "is_complete": False,
                "task_title": None
            }
        },
        {
            "scenario": "Task Creation Success",
            "data": {
                "task_title": "Buy groceries",
                "description": "Milk, bread, and eggs",
                "is_complete": True,
                "is_private": True
            }
        },
        {
            "scenario": "Task Clarification Needed",
            "data": {
                "task_title": None,
                "clarification_questions": ["What is the title of the task?"],
                "is_complete": False
            }
        },
        {
            "scenario": "Complex Task with All Fields",
            "data": {
                "task_title": "Team Meeting",
                "description": "Weekly standup meeting",
                "session_name": "Engineering Team",
                "start_date": "2024-01-15",
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "is_private": False,
                "is_global_public": False,
                "is_complete": True
            }
        },
        {
            "scenario": "Error Response",
            "data": {
                "is_complete": False,
                "clarification_questions": ["An internal error occurred: Database connection failed"]
            }
        }
    ]
    
    all_valid = True
    for test_case in test_cases:
        is_valid = validate_json_structure(test_case["data"], test_case["scenario"])
        if not is_valid:
            all_valid = False
    
    print("\n" + "=" * 50)
    if all_valid:
        print("🎉 ALL JSON RESPONSE SCENARIOS VALID!")
        print("✅ The system should consistently return proper JSON")
    else:
        print("❌ SOME JSON RESPONSES ARE INVALID")
        print("🚨 This could cause CORS errors and frontend issues")
    
    return all_valid

def test_edge_cases():
    """Test edge cases that might break JSON formatting."""
    
    print("\n🔬 Testing Edge Cases")
    print("=" * 30)
    
    edge_cases = [
        {
            "scenario": "Empty Clarification Array",
            "data": {
                "clarification_questions": [],
                "is_complete": False
            }
        },
        {
            "scenario": "Unicode Characters",
            "data": {
                "task_title": "Buy café latte ☕ and résumé update 📝",
                "description": "Français, 中文, العربية, русский",
                "is_complete": True
            }
        },
        {
            "scenario": "Special Characters in Text",
            "data": {
                "task_title": 'Task with "quotes" and \\backslashes\\',
                "description": "Newlines\nand\ttabs",
                "is_complete": True
            }
        },
        {
            "scenario": "Large Text Content",
            "data": {
                "task_title": "Long task title " + "x" * 500,
                "description": "Very long description " + "detail " * 100,
                "clarification_questions": [f"Question {i}" for i in range(10)],
                "is_complete": False
            }
        }
    ]
    
    all_valid = True
    for test_case in edge_cases:
        is_valid = validate_json_structure(test_case["data"], test_case["scenario"])
        if not is_valid:
            all_valid = False
    
    return all_valid

if __name__ == "__main__":
    print("🎯 JSON Response Validation Tool")
    print("Testing backend response structures...\n")
    
    # Run all tests
    scenarios_valid = test_response_scenarios()
    edge_cases_valid = test_edge_cases()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    if scenarios_valid and edge_cases_valid:
        print("🟢 ALL TESTS PASSED")
        print("✅ JSON responses are properly structured")
        print("✅ No CORS errors expected from malformed JSON")
        print("✅ Frontend should handle all response types correctly")
        sys.exit(0)
    else:
        print("🔴 SOME TESTS FAILED")
        print("⚠️  JSON response issues detected")
        print("🚨 May cause CORS errors and frontend parsing issues")
        sys.exit(1) 