import requests

from bs4 import BeautifulSoup

url = "https://www.formula1.com/en/racing/2025.html"
response = requests.get(url)

race_urls = []

if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    # Example: Find all relevant data
    races = soup.find_all(class_="outline-offset-4 outline-scienceBlue group outline-0 focus-visible:outline-2")
    for race in races:
        race_urls.append(race.get("href"))

else:
    print(f"Failed to fetch page: {response.status_code}")

for race_url in race_urls:
    response = requests.get(race_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    times = soup.find_all(class_="f1-racing-schedule-time")



