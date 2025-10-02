import requests
import pandas as pd
import pytz
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import json

# Load config
with open("config.json") as f:
    config = json.load(f)
API_KEY = config.get("ENTSOE_API_KEY", "")

def fetch_day_ahead_prices(zone, start, end):
    """
    Fetch day-ahead wholesale prices from ENTSO-E API.
    For now: placeholder until API key is available.
    """
    if not API_KEY:
        print("No API key found. Please update config.json")
        return None

    url = "https://web-api.tp.entsoe.eu/api"
    params = {
        "securityToken": API_KEY,
        "documentType": "A44",  # day-ahead prices
        "in_Domain": zone,
        "out_Domain": zone,
        "periodStart": start,
        "periodEnd": end,
    }

    r = requests.get(url, params=params)
    if r.status_code != 200:
        print("Error:", r.text)
        return None

    return r.text  # XML response

def parse_prices(xml_data):
    """Parse XML into DataFrame. Placeholder for now."""
    # TODO: implement XML parsing once we fetch real data
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="H"),
        "price_EUR_MWh": range(24)
    })
    return df

def normalize_to_kWh(df):
    """Convert €/MWh to €/kWh"""
    df["price_EUR_kWh"] = df["price_EUR_MWh"] / 1000
    return df

def align_timezones(df):
    """Add UTC and Europe/Nicosia columns"""
    df["timestamp_utc"] = df["timestamp"].dt.tz_localize("UTC")
    df["timestamp_cy"] = df["timestamp_utc"].dt.tz_convert("Europe/Nicosia")
    return df

def save_outputs(df, zone):
    """Export CSV + metadata JSON"""
    out_csv = f"data/{zone}_prices.csv"
    df.to_csv(out_csv, index=False)

    metadata = {
        "zone": zone,
        "source": "ENTSO-E",
        "retrieval_time": datetime.utcnow().isoformat(),
        "columns": df.columns.tolist()
    }
    with open(f"data/{zone}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved {out_csv} and metadata")

def plot_prices(df, zone):
    """Simple line plot + heatmap"""
    plt.figure(figsize=(10,5))
    plt.plot(df["timestamp_cy"], df["price_EUR_MWh"])
    plt.title(f"Day-ahead prices for {zone}")
    plt.ylabel("€/MWh")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"data/{zone}_lineplot.png")
    plt.close()

    df["hour"] = df["timestamp_cy"].dt.hour
    df["day"] = df["timestamp_cy"].dt.date
    pivot = df.pivot("day", "hour", "price_EUR_MWh")

    plt.figure(figsize=(12,6))
    sns.heatmap(pivot, cmap="viridis")
    plt.title(f"Heatmap of Day-ahead Prices for {zone}")
    plt.savefig(f"data/{zone}_heatmap.png")
    plt.close()
