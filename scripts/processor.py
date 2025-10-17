import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import xml.etree.ElementTree as ET

# Bidding zone codes
ZONE_CODES = {
    "CY": "10YCY-TSO------Q",
    "GR": "10YGR-HTSO------",
    "DE": "10Y1001A1001A83F",
    "FR": "10YFR-RTE------C",
    "ES": "10YES-REE------0",
    "IT": "10YIT-GRTN-----B",
    "NL": "10YNL----------L",
    "BE": "10YBE----------2",
}

# Load configuration
with open("config.json") as f:
    config = json.load(f)

API_KEY = config.get("api_token") or config.get("ENTSOE_API_KEY", "")


def format_entsoe_datetime(date_str, end=False):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end:
        dt += timedelta(days=1)
    return dt.strftime("%Y%m%d%H00")


def fetch_day_ahead_prices(zone, start, end):
    if not API_KEY:
        print("❌ No API key set in config.json")
        return None

    url = "https://web-api.tp.entsoe.eu/api"
    params = {
        "securityToken": API_KEY,
        "documentType": "A44",
        "in_Domain": zone,
        "out_Domain": zone,
        "periodStart": start,
        "periodEnd": end,
    }

    r = requests.get(url, params=params)
    if r.status_code != 200 or "<Acknowledgement_MarketDocument" in r.text:
        print("⚠️ No data returned for this period.")
        return None

    return r.text


def parse_prices(xml_data):
    try:
        root = ET.fromstring(xml_data)
    except Exception:
        return pd.DataFrame()

    ns = {"ns": root.tag.split("}")[0].strip("{")}
    records = []

    for ts in root.findall(".//ns:TimeSeries", ns):
        for period in ts.findall(".//ns:Period", ns):
            start_time = period.find("ns:timeInterval/ns:start", ns).text
            dt_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

            for point in period.findall("ns:Point", ns):
                pos = int(point.find("ns:position", ns).text)
                price = float(point.find("ns:price.amount", ns).text)
                ts_val = dt_start + timedelta(hours=pos - 1)
                records.append((ts_val, price))

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records, columns=["timestamp", "price_EUR_MWh"])


def normalize_to_kWh(df):
    if "price_EUR_MWh" in df.columns:
        df["price_EUR_kWh"] = df["price_EUR_MWh"] / 1000
    return df


def align_timezones(df):
    tz = config.get("timezone", "Europe/Nicosia")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if df["timestamp"].dt.tz is None:
        df["timestamp_utc"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp_utc"] = df["timestamp"].dt.tz_convert("UTC")

    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert(tz)
    return df


def save_outputs(df, zone, start, end):
    os.makedirs("data", exist_ok=True)

    export_format = config.get("export_format", "csv").lower()
    if export_format == "csv":
        out_file = f"data/{zone}_prices.csv"
        df.to_csv(out_file, index=False)
    elif export_format == "parquet":
        out_file = f"data/{zone}_prices.parquet"
        df.to_parquet(out_file, index=False)

    metadata = {
        "zone": zone,
        "source": "ENTSO-E Transparency Platform",
        "retrieval_time": datetime.now().astimezone(pytz.UTC).isoformat(),
        "period": {"start": start, "end": end},
        "normalized_to_kWh": config.get("normalize_to_kwh", True),
        "timezone": config.get("timezone", "Europe/Nicosia"),
        "columns": df.columns.tolist(),
        "record_count": len(df)
    }
    with open(f"data/{zone}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Data saved: {out_file}")


def plot_prices(df, zone):
    if df.empty:
        return

    os.makedirs("data", exist_ok=True)

    # Line plot
    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp_local"].values, df["price_EUR_MWh"].values,
             marker="o", linestyle="-", markersize=2)
    plt.title(f"Day-ahead prices for {zone}")
    plt.ylabel("€/MWh")
    plt.xlabel(f"Time ({config.get('timezone', 'local')})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"data/{zone}_lineplot.png")
    plt.close()
    print(f"✅ Line plot saved")

    # Heatmap
    df["hour"] = df["timestamp_local"].dt.hour
    df["day"] = df["timestamp_local"].dt.date
    df = df.groupby(["day", "hour"], as_index=False)["price_EUR_MWh"].mean()
    pivot = df.pivot(index="day", columns="hour", values="price_EUR_MWh")

    if not pivot.empty:
        plt.figure(figsize=(12, 6))
        sns.heatmap(pivot, cmap="viridis", cbar_kws={'label': '€/MWh'})
        plt.title(f"Heatmap of day-ahead prices for {zone}")
        plt.xlabel("Hour of day")
        plt.ylabel("Date")
        plt.tight_layout()
        plt.savefig(f"data/{zone}_heatmap.png")
        plt.close()
        print(f"✅ Heatmap saved")


if __name__ == "__main__":
    print("=" * 60)
    print("ENTSO-E Day-Ahead Price Processor")
    print("=" * 60)

    country = config.get("country_code", "CY")
    zone = ZONE_CODES.get(country, country)

    start_date = config.get("start_date", "2025-01-01")
    end_date = config.get("end_date", "2025-01-02")

    start = format_entsoe_datetime(start_date)
    end = format_entsoe_datetime(end_date, end=True)

    xml_data = fetch_day_ahead_prices(zone, start, end)
    if xml_data is None:
        print("⚠️ No data fetched, exiting.")
        exit(1)

    df = parse_prices(xml_data)
    if df.empty:
        print("⚠️ No records parsed, exiting.")
        exit(1)

    if config.get("normalize_to_kwh", True):
        df = normalize_to_kWh(df)

    df = align_timezones(df)

    save_outputs(df, zone, start, end)

    if config.get("make_plots", True):
        plot_prices(df, zone)

    print("\n✅ Finished!")
