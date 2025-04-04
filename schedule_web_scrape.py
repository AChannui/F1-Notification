import errno
import logging
import pprint
import re

import pytz
import requests
from datetime import datetime

from dynaconf import settings
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_race_urls():
    """
    Scrapes the Formula 1 website to get URLs for all races in the 2025 season.

    Returns:
        list: A list of URLs for each race in the 2025 F1 season.
    """
    url = "https://www.formula1.com/en/racing/2025.html"

    # Add error handling for the request
    try:
        response = requests.get(url, timeout=10)  # Added timeout for better error handling
        response.raise_for_status()  # Will raise an exception for 4XX/5XX responses
    except requests.RequestException as e:
        logging.error(f"Error fetching F1 race data: {e}")
        return []  # Return empty list instead of potentially undefined variable

    race_urls = []

    # Parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")

    # Find race links by their CSS class
    # This targets the clickable race card elements on the F1 website
    races = soup.find_all(class_="outline-offset-4 outline-scienceBlue group outline-0 focus-visible:outline-2")

    # Extract and construct full URLs for each race
    for race in races:
        race_url = f"https://www.formula1.com{race.get('href')}"
        race_urls.append(race_url)
        logging.debug(f"Found race URL: {race_url}")  # Optional debugging

    # Log summary of results
    if race_urls:
        logging.info(f"Found {len(race_urls)} race URLs for the 2025 season")
    else:
        logging.warning("No race URLs found. The website structure may have changed.")

    return race_urls


def parse_date(year: str, month: str, day: str, time: str):
    """
    Converts date strings into a datetime object after validation.

    Args:
        year: Four-digit year string (e.g., '2025')
        month: Three-letter month abbreviation (e.g., 'Mar')
        day: Two-digit day (e.g., '05')
        time: Time in HH:MM format (e.g., '14:30')

    Returns:
        datetime: Combined datetime object

    Raises:
        ValueError: If any component fails validation
    """
    # Define validation patterns and format codes
    patterns = {
        "year": (r"\d{4}", "%Y"),
        "month": (r"[a-zA-Z]{3}", "%b"),
        "day": (r"\d{1,2}", "%d"),
        "time": (r"\d{2}:\d{2}", "%H:%M")
    }

    # Store validated components
    matches = {}

    # Validate each component
    for param_name, param_value in [("year", str(year)), ("month", month), ("day", day), ("time", time)]:
        regex_pattern, _ = patterns[param_name]
        match = re.search(regex_pattern, param_value)
        temp = day

        if not match:
            raise ValueError(f"Invalid {param_name} value: {param_value}")

        matches[param_name] = match.group()

    # Build format string for datetime parsing
    date_format = " ".join([patterns[p][1] for p in ["year", "month", "day", "time"]])

    # Combine components into single string
    date_string = f"{matches['year']} {matches['month']} {matches['day']} {matches['time']}"

    # Parse and return datetime object
    return datetime.strptime(date_string, date_format)


def scrape_dates(race_url: str):
    time_response = requests.get(race_url)
    time_response.raise_for_status()

    time_soup = BeautifulSoup(time_response.content, "html.parser")

    all_days = time_soup.find_all("p",
                                  class_="f1-heading tracking-normal text-fs-18px leading-none normal-case font-normal non-italic f1-heading__body font-formulaOne")
    all_months = time_soup.find_all(
        class_="rounded-xl py-0.5 px-2 mt-1 leading-none inline-block bg-lightGray text-grey-70")
    all_times = time_soup.find_all("p",
                                   class_="f1-text font-titillium tracking-normal font-normal non-italic normal-case leading-none f1-text__micro text-fs-15px")

    events = time_soup.find_all("span",
                                class_="f1-heading tracking-normal text-fs-18px leading-tight normal-case font-bold non-italic f1-heading__body font-formulaOne block mb-xxs")

    event_types = []

    for index in range(len(events)):
        try:
            time = parse_date(settings['YEAR'], all_months[index].text.strip(), all_days[index].text.strip(),
                              all_times[index].text.strip())
            event_info = {
                "event": events[index].text.strip(),
                "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            event_types.append(event_info)
        except ValueError as e:
            logging.warning(f"Error parsing date: {e}, skipping")
            if not event_types:
                return None

    return event_types


def scrape_laps(race_url: str):
    lap_response = requests.get(race_url + "/circuit")
    lap_response.raise_for_status()
    lap_soup = BeautifulSoup(lap_response.content, "html.parser")
    lap_data = lap_soup.find_all("h2",
                                 class_="f1-heading tracking-normal text-fs-22px tablet:text-fs-32px leading-tight normal-case font-bold non-italic f1-heading__body font-formulaOne")
    lap_text = lap_data[1].text.strip()
    if not lap_text.isdigit():
        logging.warning(f"Laps is not a number: {lap_text}, skipping")
        return None
    laps = int(lap_data[1].text.strip())

    if 100 < laps < 30:
        logging.warning(f"Laps is out of range: {laps}, skipping")
        return None

    logging.info(f"Found {laps} laps")
    return laps


def scrape_race_data():
    race_info = []
    race_urls = get_race_urls()
    for url in race_urls:
        race_schedules = scrape_dates(url)
        race_laps = scrape_laps(url)
        if race_schedules:
            race_info.append({"url": url, "dates": race_schedules, "laps": race_laps})

    logging.info(f"Found {len(race_info)} grand prix data")
    pprint.pprint(race_info)
    return race_info


if __name__ == "__main__":
    scrape_race_data()
