import json
import logging
from datetime import datetime

import http.client
import pytz
import requests
from dynaconf import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_driver_data(meeting_key: int):
    request_url = f'https://api.openf1.org/v1/drivers?meeting_key={meeting_key}'
    response = requests.get(request_url)
    logging.info(f"Fetching driver data for meeting key {meeting_key} from {response.url}")
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as e:
        logging.error(f"Error parsing driver data JSON for meeting key {meeting_key}: {e}")
        return None

def get_session_data(meeting_key: int, session_name: str):
    request_url = f'https://api.openf1.org/v1/sessions?meeting_key={meeting_key}&session_name={session_name}'
    response = requests.get(request_url)
    logging.info(f"Fetching {session_name} session data for meeting key {meeting_key} from {response.url}")
    response.raise_for_status()
    return response.json()

def convert_to_local_time(utc_time):
    utc_time = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S%z")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    local_time = utc_time.astimezone(pytz.timezone('US/Central'))
    return local_time.strftime('%Y-%m-%d %I:%M %p')

def send_notification(message, title):
    payload = {
        'token': settings['PUSHOVER_TOKEN'],
        'user': settings['PUSHOVER_USER_KEY'],
        'title': title,
        'message': message
    }

    # uncomment to send notification
    # response = requests.post(pushover_url, data=payload)
    # response.raise_for_status()
    logging.info("Notification sent successfully.")
    return payload

def meeting_message(meeting_data):
    date_start = convert_to_local_time(meeting_data['date_start'])
    message = (
        f"Meeting: {meeting_data['meeting_name']}\n"
        f"Date & Time: {date_start}\n"
        f"Location: {meeting_data['location']} {meeting_data['country_name']}\n"
    )
    return message

def grand_prix_message(session_data, weather_data):
    date_start = convert_to_local_time(session_data['date_start'])
    message = (
        f"{session_data['country_name']} Grand Prix\n"
        f"Time: {date_start}\n"
        f"Weather: "
    )



def main():
    # Fetch meetings data
    response = requests.get(f'https://api.openf1.org/v1/meetings?year={settings["YEAR"]}')
    logging.info(f"Fetching meetings data from {response.url}: year {settings['YEAR']}")
    response.raise_for_status()

    try:
        meeting_data = response.json()
    except ValueError as e:
        logging.error(f"Error parsing meetings data JSON: {e}")
        return

    # Process each meeting
    driver_dict = dict()
    for meeting in meeting_data:
        meeting_key = meeting.get('meeting_key')
        if not meeting_key:
            logging.warning("Missing 'meeting_key' in meeting data.")
            continue

        driver_data = get_driver_data(meeting_key)
        if driver_data:
            driver_dict[meeting_key] = driver_data

    logging.info(f"Successfully fetched meetings data. Total meetings: {len(meeting_data)}")
    print(send_notification(meeting_data[1])['message'])


# Entry point
if __name__ == '__main__':
    main()

#TODO find circuit laps - thinking hard code map
#TODO change time to report grand prix time not start time - maybe try web scrape of f1 site
#TODO write different messages - like over take, sprint start time, final results
#TODO figure out how to find out the start of a race/schedule