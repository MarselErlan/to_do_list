#!/usr/bin/env python3
"""Test script to verify time parsing logic."""

from datetime import date, time
from typing import Optional

def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string with robust error handling."""
    if not isinstance(date_str, str):
        return None
    try:
        # Handle ISO datetime format (extract date part)
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None

def parse_time(time_str: Optional[str]) -> Optional[time]:
    """Parse time string with robust error handling."""
    if not isinstance(time_str, str):
        return None
    try:
        # Handle ISO datetime format (extract time part)
        if 'T' in time_str:
            time_str = time_str.split('T')[1]
        # Remove timezone info if present
        if '+' in time_str:
            time_str = time_str.split('+')[0]
        if 'Z' in time_str:
            time_str = time_str.replace('Z', '')
        # Ensure format is HH:MM:SS
        if len(time_str.split(':')) == 2:
            time_str += ':00'
        return time.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None

# Test cases
test_cases = [
    # Test problematic format from the error
    "2025-07-09T15:15:00",
    # Test normal formats
    "2025-01-15",
    "14:30:00",
    "14:30",
    # Test edge cases
    "2025-01-15T14:30:00Z",
    "2025-01-15T14:30:00+00:00",
    None,
    "",
    "invalid"
]

print("Testing time parsing logic:")
for test_str in test_cases:
    parsed_date = parse_date(test_str)
    parsed_time = parse_time(test_str)
    print(f"Input: {test_str}")
    print(f"  Date: {parsed_date}")
    print(f"  Time: {parsed_time}")
    print() 