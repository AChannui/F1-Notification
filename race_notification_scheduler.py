import json
import logging

import boto3
import pytz
from datetime import datetime, timedelta
from schedule_web_scrape import scrape_race_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):
    # Scrape current race data
    logger.info("Scraping F1 race schedule data")
    race_data = scrape_race_data()

    # Get current time in UTC
    now = datetime.now(pytz.UTC)
    logger.info(f"Current time: {now.isoformat()}")

    # Initialize Step Functions client
    stepfunctions = boto3.client('stepfunctions')

    # Track events we've scheduled
    scheduled_events = 0

    # Process each race
    for race in race_data:
        # Extract circuit info from URL
        circuit = race.get('url', '').split('/')[-1].replace('-', ' ').title()
        laps = race.get('laps', 'N/A')

        # Process each event in the race weekend
        for event in race['dates']:
            event_time_iso = event['date']
            event_time = datetime.fromisoformat(event_time_iso)
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=pytz.UTC)

            event_name = event['event']

            # Skip past events
            if event_time <= now:
                logger.info(f"Skipping past event: {event_name} at {event_time.isoformat()}")
                continue

            # Calculate notification time (5 minutes before event)
            notification_time = event_time - timedelta(minutes=5)

            # Skip if notification time has already passed
            if notification_time <= now:
                logger.info(f"Skipping event with past notification time: {event_name}")
                continue

            # Calculate wait time in seconds
            wait_seconds = (notification_time - now).total_seconds()

            # Only schedule events in the next 24 hours
            # Step Functions has limitations on wait times and we want to be efficient
            if wait_seconds > 86400:  # 24 hours in seconds
                logger.info(f"Skipping event too far in future: {event_name}, would wait {wait_seconds / 3600} hours")
                continue

            # Create event info to pass to the notification Lambda
            event_info = {
                "event_name": event_name,
                "event_time": event_time.isoformat(),
                "notification_time": notification_time.isoformat(),
                "circuit": circuit,
                "laps": laps
            }

            # Generate a unique name for this execution (Step Functions requirement)
            execution_name = f"f1-notification-{event_name.replace(' ', '-')}-{event_time.strftime('%Y%m%d%H%M')}"

            # Execute the state machine (which will wait and then notify)
            logger.info(f"Scheduling notification for {event_name} at {notification_time.isoformat()}")
            response = stepfunctions.start_execution(
                stateMachineArn='arn:aws:states:region:account-id:stateMachine:F1NotificationStateMachine',
                name=execution_name[:80],  # Step Functions has 80 char limit on name
                input=json.dumps({
                    "event": event_info,
                    "wait_seconds": int(wait_seconds)
                })
            )

            logger.info(f"Step Functions execution started: {response['executionArn']}")
            scheduled_events += 1

    logger.info(f"Scheduled {scheduled_events} event notifications")

    return {
        'statusCode': 200,
        'body': json.dumps(f'Scheduled {scheduled_events} event notifications')
    }

if __name__ == '__main__':
    lambda_handler(None, None)