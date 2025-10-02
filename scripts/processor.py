import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os

# Mapping of bidding zone codes (ENTSO-E requires these IDs, not just country codes)
ZONE_CODES = {
    "CY": "10YCY-TSO------Q",   # Cyprus
    "GR": "10YGR-HTSO------A",  # Greece
    "DE": "10Y1001A1001A83F"    # Germany
}

# Load config
with open("config.json") as f:
    config = json.load(f)

API_KEY = config.get("ENTSOE_API_KEY", "")


def format_entsoe_datetime(date_str, end=False):
    """
    Convert YYYY-MM-DD -> ENTSO-E format YYYYMMDDHH00
    If end=True, set time to 23:00, else 00:00
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end:
        dt += timedelta(hours=23)
    return dt.strftime("%Y%m%d%H00")


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
        print("Error fetching data:", r.text)
        return None

    return r.text  # XML response


def parse_prices(xml_data):
    """
    Parse XML into DataFrame.
    For now: dummy placeholder until XML parsing is implemented.
    """
    # TODO: Implement real XML parsing (lxml or xml.etree)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=48, freq="h"),
        "price_EUR_MWh": list(range(24)) * 2
    })
    return df


def normalize_to_kWh(df):
    """Convert €/MWh to €/kWh"""
    df["price_EUR_kWh"] = df["price_EUR_MWh"] / 1000
    return df


def align_timezones(df):
    """Add UTC and configured timezone columns"""
    tz = config.get("timezone", "Europe/Nicosia")
    df["timestamp_utc"] = df["timestamp"].dt.tz_localize("UTC")
    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert(tz)
    return df


def save_outputs(df, zone, start, end):
    """Export CSV + metadata JSON"""
    os.makedirs("data", exist_ok=True)

    export_format = config.get("export_format", "csv").lower()

    if export_format == "csv":
        out_file = f"data/{zone}_prices.csv"
        df.to_csv(out_file, index=False)
    elif export_format == "parquet":
        out_file = f"data/{zone}_prices.parquet"
        df.to_parquet(out_file, index=False)
    else:
        raise ValueError("Unsupported export_format in config.json")

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

    print(f"Saved {out_file} and metadata")


def plot_prices(df, zone):
    """Simple line plot + heatmap"""
    os.makedirs("data", exist_ok=True)

    # Line plot
    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp_local"], df["price_EUR_MWh"])
    plt.title(f"Day-ahead prices for {zone}")
    plt.ylabel("€/MWh")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"data/{zone}_lineplot.png")
    plt.close()

    # Heatmap
    df["hour"] = df["timestamp_local"].dt.hour
    df["day"] = df["timestamp_local"].dt.date
    pivot = df.pivot(index="day", columns="hour", values="price_EUR_MWh")

    plt.figure(figsize=(12, 6))
    sns.heatmap(pivot, cmap="viridis")
    plt.title(f"Heatmap of Day-ahead Prices for {zone}")
    plt.savefig(f"data/{zone}_heatmap.png")
    plt.close()


if __name__ == "__main__":
    # Pick zone from config
    country = config.get("country_code", "CY")
    zone = ZONE_CODES.get(country, country)

    # Format start and end dates for ENTSO-E
    start = format_entsoe_datetime(config.get("start_date", "2025-01-01"))
    end = format_entsoe_datetime(config.get("end_date", "2025-01-02"), end=True)

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
