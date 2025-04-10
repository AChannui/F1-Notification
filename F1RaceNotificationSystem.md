# F1 Race Notification System

An automated system for monitoring Formula 1 race schedules and delivering notifications about upcoming race events.

## Current Features

- Scrapes F1 race schedules from the web to get up-to-date information
- Schedules notifications for upcoming race events (practices, qualifying, races)
- Sends notifications 5 minutes before each race event begins
- AWS serverless architecture using Lambda and Step Functions
- Handles time zones correctly with UTC standardization

## How It Works

1. The system periodically scrapes F1 race schedule data
2. For each upcoming event, it calculates the time until notification (5 mins before event)
3. Events occurring within the next 24 hours are scheduled for notification
4. AWS Step Functions handles the notification timing
5. When an event is about to begin, users receive a notification with event details

## Project Structure

- `race_notification_scheduler.py`: Main Lambda handler for scheduling notifications
- `schedule_web_scrape.py`: Web scraping functionality to get race schedule data
- `race_notification_sender.py`: Sends the actual notifications when events are upcoming
- `main.py`: Entry point for manual testing and development

## Planned Features

- **Race Update Notifications**: Real-time updates during races including:
  - Fastest lap notifications
  - Overtake alerts
  - Pit stop information
  - Race position changes
  - Safety car/yellow flag notifications

## Technical Details

- Built with Python 3
- Uses AWS services: Lambda, Step Functions
- Uses Pushover: SNS (for notifications)
- Dependencies: boto3, pytz, requests

## Development Status

This project is currently under active development. The core notification system for race events is working, but real-time race updates are still being implemented.

## Getting Started

(This section will be expanded as the project progresses)

---

*Note: This README is subject to change as the project evolves.*