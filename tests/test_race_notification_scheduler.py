import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
from race_notification_scheduler import lambda_handler


@pytest.fixture
def mock_event():
    return {}


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.fixture
def sample_race_data():
    now = datetime.now(pytz.UTC)
    return [
        {
            'url': 'https://example.com/monaco-grand-prix',
            'laps': 78,
            'date': [
                {
                    'date': now + timedelta(hours=2),  # Soon event
                    'event': 'Practice 1'
                },
                {
                    'date': now + timedelta(hours=26),  # Beyond 24hr window
                    'event': 'Practice 2'
                },
                {
                    'date': now - timedelta(hours=2),  # Past event
                    'event': 'Past Session'
                },
                {
                    'date': now + timedelta(minutes=3),  # Too soon for notification
                    'event': 'Almost Now Session'
                }
            ]
        }
    ]


class TestRaceNotificationScheduler:

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_no_races(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        mock_scrape.return_value = []
        mock_datetime.now.return_value = datetime.now(pytz.UTC)
        mock_stepfunctions = MagicMock()
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 0 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_not_called()

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_all_past_events(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_datetime.now.return_value = now
        mock_scrape.return_value = [{
            'url': 'https://example.com/past-grand-prix',
            'laps': 50,
            'date': [
                {
                    'date': now - timedelta(hours=2),
                    'event': 'Past Session 1'
                },
                {
                    'date': now - timedelta(hours=1),
                    'event': 'Past Session 2'
                }
            ]
        }]
        mock_stepfunctions = MagicMock()
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 0 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_not_called()

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_events_within_24_hours(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_now = MagicMock(wraps=now)
        mock_now.__ge__ = lambda self, other: now >= other
        mock_now.__gt__ = lambda self, other: now > other
        mock_now.__le__ = lambda self, other: now <= other
        mock_now.__lt__ = lambda self, other: now < other
        mock_now.isoformat.return_value = now.isoformat()

        mock_datetime.now.return_value = mock_now

        # Event in 6 hours
        event_time = now + timedelta(hours=6)
        notification_time = event_time - timedelta(minutes=5)

        mock_scrape.return_value = [{
            'url': 'https://example.com/upcoming-grand-prix',
            'laps': 55,
            'date': [
                {
                    'date': event_time,
                    'event': 'Qualifying'
                }
            ]
        }]

        mock_stepfunctions = MagicMock()
        mock_stepfunctions.start_execution.return_value = {
            'executionArn': 'test-arn'
        }
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 1 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_called_once()

        # Verify the execution details
        call_args = mock_stepfunctions.start_execution.call_args[1]
        assert 'f1-notification-Qualifying-' in call_args['name']

        input_payload = json.loads(call_args['input'])
        assert input_payload['event']['event_name'] == 'Qualifying'
        assert input_payload['event']['circuit'] == 'Upcoming Grand Prix'
        assert input_payload['event']['laps'] == 55
        assert input_payload['wait_seconds'] < 86400  # Less than 24 hours

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_events_beyond_24_hours(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_now = MagicMock(wraps=now)
        mock_now.__ge__ = lambda self, other: now >= other
        mock_now.__gt__ = lambda self, other: now > other
        mock_now.__le__ = lambda self, other: now <= other
        mock_now.__lt__ = lambda self, other: now < other
        mock_now.isoformat.return_value = now.isoformat()

        mock_datetime.now.return_value = mock_now

        # Event in 48 hours
        event_time = now + timedelta(hours=48)

        mock_scrape.return_value = [{
            'url': 'https://example.com/future-grand-prix',
            'laps': 60,
            'date': [
                {
                    'date': event_time,
                    'event': 'Future Race'
                }
            ]
        }]

        mock_stepfunctions = MagicMock()
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 0 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_not_called()

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_notification_time_passed(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_datetime.now.return_value = now

        # Event in 3 minutes (notification time already passed)
        event_time = now + timedelta(minutes=3)

        mock_scrape.return_value = [{
            'url': 'https://example.com/imminent-grand-prix',
            'laps': 45,
            'date': [
                {
                    'date': event_time,
                    'event': 'Imminent Session'
                }
            ]
        }]

        mock_stepfunctions = MagicMock()
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 0 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_not_called()

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_mixed_event_scenarios(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context,
                                   sample_race_data):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_now = MagicMock(wraps=now)
        mock_now.__ge__ = lambda self, other: now >= other
        mock_now.__gt__ = lambda self, other: now > other
        mock_now.__le__ = lambda self, other: now <= other
        mock_now.__lt__ = lambda self, other: now < other
        mock_now.isoformat.return_value = now.isoformat()

        mock_datetime.now.return_value = mock_now
        mock_scrape.return_value = sample_race_data

        mock_stepfunctions = MagicMock()
        mock_stepfunctions.start_execution.return_value = {
            'executionArn': 'test-arn'
        }
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 1 event notifications" in result['body']
        mock_stepfunctions.start_execution.assert_called_once()

        # Should only schedule the event that's in 2 hours
        call_args = mock_stepfunctions.start_execution.call_args[1]
        input_payload = json.loads(call_args['input'])
        assert input_payload['event']['event_name'] == 'Practice 1'
        assert input_payload['event']['circuit'] == 'Monaco Grand Prix'

    @patch('race_notification_scheduler.scrape_race_data')
    @patch('race_notification_scheduler.boto3.client')
    @patch('race_notification_scheduler.datetime')
    def test_execution_name_truncation(self, mock_datetime, mock_boto3, mock_scrape, mock_event, mock_context):
        # Setup
        now = datetime.now(pytz.UTC)
        mock_now = MagicMock(wraps=now)
        mock_now.isoformat.return_value = now.isoformat()
        mock_datetime.now.return_value = mock_now

        # Event with a very long name
        event_time = now + timedelta(hours=6)

        very_long_event_name = "This is an extremely long event name that would definitely exceed the Step Functions 80 character limit when combined with the timestamp and prefix"

        mock_scrape.return_value = [{
            'url': 'https://example.com/long-name-grand-prix',
            'laps': 55,
            'date': [
                {
                    'date': event_time,
                    'event': very_long_event_name
                }
            ]
        }]

        mock_stepfunctions = MagicMock()
        mock_stepfunctions.start_execution.return_value = {
            'executionArn': 'test-arn'
        }
        mock_boto3.return_value = mock_stepfunctions

        # Execute
        result = lambda_handler(mock_event, mock_context)

        # Verify
        assert result['statusCode'] == 200
        assert "Scheduled 1 event notifications" in result['body']

        # Verify name was truncated to 80 chars
        call_args = mock_stepfunctions.start_execution.call_args[1]
        assert len(call_args['name']) <= 80