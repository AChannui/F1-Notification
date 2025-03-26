import pytest

from main import convert_to_local_time

def test_convert_to_local_time():
    """Test conversion of valid UTC time to local time (CST)"""
    utc_time = "2025-06-15T14:00:00Z"
    result = convert_to_local_time(utc_time)
    assert result == "2025-06-15 09:00:00"

def test_convert_to_local_time_invalid_format():
    """Test conversion with invalid time format"""
    utc_time = "2025-15-06T14:00:00"  # Invalid format
    with pytest.raises(ValueError):
        convert_to_local_time(utc_time)

def test_send_notification():
    """Test sending notification"""

    pass