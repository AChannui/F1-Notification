import pytest
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
import race_notification_sender  # Assuming this is the name of the module


@pytest.fixture
def valid_event():
    return {
        'event_name': 'Monaco Grand Prix',
        'event_time': '2023-05-28T14:00:00Z',
        'circuit': 'Circuit de Monaco',
        'laps': 78
    }


@pytest.fixture
def mock_env_variables():
    """Set up mock environment variables"""
    with patch.dict(os.environ, {
        'PUSHOVER_TOKEN': 'test_token',
        'PUSHOVER_USER_KEY': 'test_user_key'
    }):
        yield


@pytest.fixture
def mock_successful_response():
    """Mock a successful response from Pushover API"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"
    return mock_response


@pytest.fixture
def mock_failed_response():
    """Mock a failed response from Pushover API"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Error: invalid token"
    return mock_response


def test_send_notification_success(mock_env_variables, mock_successful_response):
    """Test successful notification sending to Pushover"""
    with patch('requests.post', return_value=mock_successful_response) as mock_post:
        status_code = race_notification_sender.send_notification(
            "Test message", "Test title"
        )

        # Verify status code
        assert status_code == 200

        # Verify the request was made with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://api.pushover.net/1/messages.json'
        assert kwargs['data']['token'] == 'test_token'
        assert kwargs['data']['user'] == 'test_user_key'
        assert kwargs['data']['message'] == 'Test message'
        assert kwargs['data']['title'] == 'Test title'


def test_send_notification_failure(mock_env_variables, mock_failed_response):
    """Test failed notification sending to Pushover"""
    with patch('requests.post', return_value=mock_failed_response) as mock_post:
        status_code = race_notification_sender.send_notification(
            "Test message", "Test title"
        )

        # Verify status code
        assert status_code == 400

        # Verify the request was made
        mock_post.assert_called_once()


def test_lambda_handler_success(valid_event, mock_env_variables, mock_successful_response):
    """Test successful lambda execution"""
    with patch('requests.post', return_value=mock_successful_response) as mock_post:
        response = race_notification_sender.lambda_handler(valid_event, {})

        # Verify the response
        assert response['statusCode'] == 200
        assert 'Notification sent successfully' in response['body']

        # Verify Pushover API was called with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        # Check the message content
        assert 'Monaco Grand Prix STARTING IN 5 MINUTES' in kwargs['data']['message']
        assert 'Circuit: Circuit de Monaco' in kwargs['data']['message']
        assert 'Laps: 78' in kwargs['data']['message']

        # Check the title
        assert kwargs['data']['title'] == 'F1 STARTING SOON: Monaco Grand Prix'


def test_lambda_handler_missing_circuit_laps(mock_env_variables, mock_successful_response):
    """Test with missing optional fields"""
    event = {
        'event_name': 'Monaco Grand Prix',
        'event_time': '2023-05-28T14:00:00Z'
    }

    with patch('requests.post', return_value=mock_successful_response) as mock_post:
        response = race_notification_sender.lambda_handler(event, {})

        assert response['statusCode'] == 200

        # Verify default values are used
        args, kwargs = mock_post.call_args
        assert 'Circuit: Unknown Circuit' in kwargs['data']['message']
        assert 'Laps: N/A' in kwargs['data']['message']


def test_lambda_handler_missing_required_fields():
    """Test with missing required fields"""
    event = {
        'event_time': '2023-05-28T14:00:00Z'
    }

    response = race_notification_sender.lambda_handler(event, {})

    assert response['statusCode'] == 500
    assert 'Error' in response['body']


def test_lambda_handler_invalid_date_format():
    """Test with invalid date format"""
    event = {
        'event_name': 'Monaco Grand Prix',
        'event_time': 'invalid-date-format',
        'circuit': 'Circuit de Monaco',
        'laps': 78
    }

    response = race_notification_sender.lambda_handler(event, {})

    assert response['statusCode'] == 500
    assert 'Error' in response['body']


def test_pushover_api_error(valid_event, mock_env_variables, mock_failed_response):
    """Test handling of Pushover API errors"""
    with patch('requests.post', return_value=mock_failed_response) as mock_post:
        response = race_notification_sender.lambda_handler(valid_event, {})

        # Should return the Pushover API status code
        assert response['statusCode'] == 400


def test_message_formatting(mock_env_variables, mock_successful_response):
    """Test the correct formatting of the notification message"""
    event = {
        'event_name': 'Monaco Grand Prix',
        'event_time': '2023-05-28T14:00:00Z',
        'circuit': 'Circuit de Monaco',
        'laps': 78
    }

    with patch('requests.post', return_value=mock_successful_response) as mock_post:
        race_notification_sender.lambda_handler(event, {})

        # Verify the message format
        args, kwargs = mock_post.call_args
        message = kwargs['data']['message']

        # Check all required elements in the message
        assert '⚠️ Monaco Grand Prix STARTING IN 5 MINUTES ⚠️' in message
        assert 'Event: Monaco Grand Prix' in message
        assert 'Start Time: 2023-05-28 02:00 PM UTC' in message
        assert 'Circuit: Circuit de Monaco' in message
        assert 'Laps: 78' in message


def test_lambda_handler_missing_env_variables(valid_event):
    """Test missing environment variables"""
    with patch.dict(os.environ, {}, clear=True):
        with patch('requests.post') as mock_post:
            response = race_notification_sender.lambda_handler(valid_event, {})

            # Should fail due to missing environment variables
            assert response['statusCode'] == 500
            assert 'Error' in response['body']

            # Verify no API call was attempted
            mock_post.assert_not_called()