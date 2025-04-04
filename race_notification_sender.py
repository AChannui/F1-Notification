import json
import logging
import os
from datetime import datetime

import requests
from dynaconf import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def send_notification(message, title):
    # Get environment variables
    pushover_token = os.environ.get('PUSHOVER_TOKEN')
    pushover_user_key = os.environ.get('PUSHOVER_USER_KEY')

    pushover_token = settings['PUSHOVER_TOKEN']
    pushover_user_key = settings['PUSHOVER_USER_KEY']

    payload = {
        'token': pushover_token,
        'user': pushover_user_key,
        'title': title,
        'message': message,
    }

    pushover_url = 'https://api.pushover.net/1/messages.json'
    response = requests.post(pushover_url, data=payload)

    if response.status_code == 200:
        logger.info("Notification sent successfully")
    else:
        logger.error(f"Failed to send notification: {response.text}")

    return response.status_code


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract event details
        event_name = event['event_name']
        event_time = datetime.fromisoformat(event['event_time'].replace('Z', '+00:00'))
        circuit = event.get('circuit', 'Unknown Circuit')
        laps = event.get('laps', 'N/A')

        # Format the event time in a readable format
        formatted_time = event_time.strftime('%Y-%m-%d %I:%M %p UTC')

        # Create notification message
        message = (
            f"⚠️ {event_name} STARTING IN 5 MINUTES ⚠️\n\n"
            f"Event: {event_name}\n"
            f"Start Time: {formatted_time}\n"
            f"Circuit: {circuit}\n"
            f"Laps: {laps}"
        )

        # Send notification
        title = f"F1 STARTING SOON: {event_name}"
        status_code = send_notification(message, title)

        return {
            'statusCode': status_code,
            'body': json.dumps('Notification sent successfully')
        }

    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


if __name__ == '__main__':
    package = (
        {
            "event": {
                "event_name": "Race",
                "event_time": "2021-01-01T00:00:00Z",
                "notification_time": "2021-01-01T00:05:00Z",
                "circuit": "Circuit 1",
                "laps": "10"
            }
        }
    )


    lambda_handler(package, None)