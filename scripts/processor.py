import requests
import pandas as pd
import pytz
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os

# Mapping of bidding zone codes (ENTSO-E requires these IDs, not just country codes)
ZONE_CODES = {
    "CY": "10Y1001A1001B012",
    "GR": "10YGR-HTSO------A",
    "DE": "10Y1001A1001A83F"
}

# Load config
with open("config.json") as f:
    config = json.load(f)

API_KEY = config.get("ENTSOE_API_KEY", "")

def fetch_day_ahead_prices(zone, start, end):
    """
    Fetch day-ahead wholesale prices from ENTSO-E API.
    Returns raw XML string.
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
    """Parse XML into DataFrame. For now: dummy data until API key works."""
    # TODO: implement XML parsing once we fetch real data
    df = pd.DataFrame({
    "timestamp": pd.date_range("2025-01-01", periods=24, freq="h"),
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

def save_outputs(df, zone, start, end):
    """Export CSV + metadata JSON"""
    os.makedirs("data", exist_ok=True)
    out_csv = f"data/{zone}_prices.csv"
    df.to_csv(out_csv, index=False)

    metadata = {
        "zone": zone,
        "source": "ENTSO-E Transparency Platform",
        "retrieval_time": datetime.now().astimezone(pytz.UTC).isoformat(),
        "period": {"start": start, "end": end},
        "normalized_to_kWh": config.get("normalize_to_kwh", True),
        "timezone": config.get("timezone", "Europe/Nicosia"),
        "columns": df.columns.tolist()
    }
    with open(f"data/{zone}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved {out_csv} and metadata")

def plot_prices(df, zone):
    """Simple line plot + heatmap"""
    os.makedirs("data", exist_ok=True)

    # Line plot
    plt.figure(figsize=(10,5))
    plt.plot(df["timestamp_cy"], df["price_EUR_MWh"])
    plt.title(f"Day-ahead prices for {zone}")
    plt.ylabel("€/MWh")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"data/{zone}_lineplot.png")
    plt.close()

    # Heatmap
    df["hour"] = df["timestamp_cy"].dt.hour
    df["day"] = df["timestamp_cy"].dt.date
    pivot = df.pivot(index="day", columns="hour", values="price_EUR_MWh")

    plt.figure(figsize=(12,6))
    sns.heatmap(pivot, cmap="viridis")
    plt.title(f"Heatmap of Day-ahead Prices for {zone}")
    plt.savefig(f"data/{zone}_heatmap.png")
    plt.close()


if __name__ == "__main__":
    # Pick zone from config
    country = config.get("country_code", "CY")
    zone = ZONE_CODES.get(country, country)

    start = config.get("start_date", "202501010000")
    end = config.get("end_date", "202501022300")

    xml_data = fetch_day_ahead_prices(zone, start, end)

    if xml_data is None:
        print("Using placeholder data...")
        df = parse_prices(None)
    else:
        df = parse_prices(xml_data)

    if config.get("normalize_to_kwh", True):
        df = normalize_to_kWh(df)

    df = align_timezones(df)

    save_outputs(df, zone, start, end)

    if config.get("make_plots", True):
        plot_prices(df, zone)
