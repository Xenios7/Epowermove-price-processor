import requests, json, pandas as pd
from datetime import datetime
import pytz

with open("config.json") as f:
    config = json.load(f)

TOKEN = config["api_token"]
COUNTRY = config["country_code"]
START = config["start_date"]
END = config["end_date"]

# Example URL for day-ahead prices
url = (
    f"https://transparency.entsoe.eu/api?documentType=A44"
    f"&in_Domain={COUNTRY}&out_Domain={COUNTRY}"
    f"&periodStart={START}0000&periodEnd={END}2300"
    f"&securityToken={TOKEN}"
)

print("Fetching data from:", url)
response = requests.get(url)
if response.status_code == 200:
    print("Success!")
    # TODO: Parse XML -> DataFrame
else:
    print("Error:", response.status_code, response.text)
    