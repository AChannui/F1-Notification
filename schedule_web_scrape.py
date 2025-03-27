import logging
import pprint
import re
import requests
from datetime import datetime

from dynaconf import settings
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_race_urls():
    url = "https://www.formula1.com/en/racing/2025.html"
    response = requests.get(url)

    race_urls = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        # Example: Find all relevant data
        races = soup.find_all(class_="outline-offset-4 outline-scienceBlue group outline-0 focus-visible:outline-2")
        for race in races:
            race_urls.append(f"https://www.formula1.com{race.get("href")}")

    else:
        logging.error(f"Failed to fetch data from {url}")

    return race_urls

def scrape_dates(race_url: str):
    time_response = requests.get(race_url)
    time_response.raise_for_status()

    time_soup = BeautifulSoup(time_response.content, "html.parser")
    day = time_soup.find("p", class_="f1-heading tracking-normal text-fs-18px leading-none normal-case font-normal non-italic f1-heading__body font-formulaOne")
    month = time_soup.find(class_="rounded-xl py-0.5 px-2 mt-1 leading-none inline-block bg-lightGray text-grey-70")
    time = time_soup.find("p", class_="f1-text font-titillium tracking-normal font-normal non-italic normal-case leading-none f1-text__micro text-fs-15px")


    if day and month and time:
        day = day.text.strip()
        month = month.text.strip()
        time = time.text.strip()
        if re.match(r"\d{2}:\d{2}", time):
            race_date = datetime.strptime(f"{settings['YEAR']} {day} {month} {time}", "%Y %d %b %H:%M")
            if race_date > datetime.now():
                logging.info(f"Found date: {race_date}")
                return race_date
            else:
                logging.warning(f"Date is in the past: {race_date}")
        else:
            logging.warning(f"Time is not in the correct format: {time}, skipping")


def scrape_laps(race_url: str):
    lap_response = requests.get(race_url + "/circuit")
    lap_response.raise_for_status()
    lap_soup = BeautifulSoup(lap_response.content, "html.parser")
    lap_data = lap_soup.find_all("h2", class_="f1-heading tracking-normal text-fs-22px tablet:text-fs-32px leading-tight normal-case font-bold non-italic f1-heading__body font-formulaOne")
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



def scrape_schedule():
    race_info = []
    race_urls = get_race_urls()
    for url in race_urls:
        race_schedule = scrape_dates(url)
        race_laps = scrape_laps(url)
        if race_schedule:
            race_info.append({"url": url, "date": race_schedule, "laps": race_laps})

    pprint.pprint(race_info)

if __name__ == "__main__":
    scrape_schedule()