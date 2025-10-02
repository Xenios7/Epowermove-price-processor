import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import xml.etree.ElementTree as ET

# Mapping of bidding zone codes (ENTSO-E requires these IDs, not just country codes)
ZONE_CODES = {
    "CY": "10YCY-TSO------Q",   # Cyprus (16 chars)
    "GR": "10YGR-HTSO------",   # Greece (16 chars)
    "DE": "10Y1001A1001A83F",   # Germany (16 chars)
    "FR": "10YFR-RTE------C",   # France (16 chars)
    "ES": "10YES-REE------0",   # Spain (16 chars)
    "IT": "10YIT-GRTN-----B",   # Italy (16 chars)
    "NL": "10YNL----------L",   # Netherlands (16 chars)
    "BE": "10YBE----------2",   # Belgium (16 chars)
}

# Load config
with open("config.json") as f:
    config = json.load(f)

API_KEY = config.get("api_token") or config.get("ENTSOE_API_KEY", "")


def format_entsoe_datetime(date_str, end=False):
    """Convert YYYY-MM-DD -> ENTSO-E format YYYYMMDDHH00"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if end:
        dt += timedelta(days=1)  # ENTSO-E expects exclusive end time
    return dt.strftime("%Y%m%d%H00")


def fetch_day_ahead_prices(zone, start, end):
    """Fetch day-ahead wholesale prices from ENTSO-E API. Returns raw XML string."""
    if not API_KEY:
        print("❌ No API key found. Please update config.json")
        return None

    url = "https://web-api.tp.entsoe.eu/api"
    params = {
        "securityToken": API_KEY,
        "documentType": "A44",   # day-ahead prices
        "in_Domain": zone,
        "out_Domain": zone,
        "periodStart": start,
        "periodEnd": end,
    }

    r = requests.get(url, params=params)
    print(f"📡 API request URL: {r.url}")
    print(f"🔑 Status code: {r.status_code}")

    if r.status_code != 200:
        print("❌ Error response:")
        print(r.text[:1000])
        return None

    if "<Acknowledgement_MarketDocument" in r.text:
        print("⚠️ API returned acknowledgement (no data available for given period).")
        try:
            root = ET.fromstring(r.text)
            ns = {"ns": root.tag.split('}')[0].strip('{')}
            reason = root.find(".//ns:Reason/ns:text", ns)
            if reason is not None:
                print(f"\n📋 Reason: {reason.text}")
        except:
            pass
        return None

    print("✅ API call succeeded, showing first 500 chars of response:")
    print(r.text[:500])
    return r.text


def parse_prices(xml_data):
    """Parse ENTSO-E XML response into DataFrame with timestamps and prices."""
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"❌ XML parsing error: {e}")
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
        print("⚠️ No price records parsed from XML.")
        return pd.DataFrame()

    df = pd.DataFrame(records, columns=["timestamp", "price_EUR_MWh"])
    print(f"✅ Parsed {len(df)} price records")
    return df


def normalize_to_kWh(df):
    """Convert €/MWh to €/kWh"""
    if "price_EUR_MWh" in df.columns:
        df["price_EUR_kWh"] = df["price_EUR_MWh"] / 1000
    return df


def align_timezones(df):
    """Add UTC and configured timezone columns"""
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
    """Export CSV/Parquet + metadata JSON"""
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
        "columns": df.columns.tolist(),
        "record_count": len(df)
    }
    with open(f"data/{zone}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Saved {out_file} and metadata")


def plot_prices(df, zone):
    """Simple line plot + heatmap"""
    if df.empty:
        print("⚠️ No data available for plotting.")
        return

    os.makedirs("data", exist_ok=True)

    # Line plot
    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp_local"], df["price_EUR_MWh"])
    plt.title(f"Day-ahead prices for {zone}")
    plt.ylabel("€/MWh")
    plt.xlabel(f"Time ({config.get('timezone', 'local')})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"data/{zone}_lineplot.png")
    plt.close()
    print(f"✅ Saved line plot: data/{zone}_lineplot.png")

    # Heatmap
    df["hour"] = df["timestamp_local"].dt.hour
    df["day"] = df["timestamp_local"].dt.date
    pivot = df.pivot_table(index="day", columns="hour", values="price_EUR_MWh", aggfunc="mean")

    if pivot.empty:
        print("⚠️ Heatmap skipped: no data available for given period")
        return

    plt.figure(figsize=(12, 6))
    sns.heatmap(pivot, cmap="viridis", cbar_kws={'label': '€/MWh'})
    plt.title(f"Heatmap of Day-ahead Prices for {zone}")
    plt.xlabel("Hour of day")
    plt.ylabel("Date")
    plt.tight_layout()
    plt.savefig(f"data/{zone}_heatmap.png")
    plt.close()
    print(f"✅ Saved heatmap: data/{zone}_heatmap.png")


if __name__ == "__main__":
    print("=" * 60)
    print("ENTSO-E Day-Ahead Price Processor")
    print("=" * 60)

    country = config.get("country_code", "CY")
    zone = ZONE_CODES.get(country, country)
    print(f"\n🌍 Country: {country}")
    print(f"📍 Zone code: {zone}")

    start_date = config.get("start_date", "2025-01-01")
    end_date = config.get("end_date", "2025-01-02")
    print(f"📅 Date range: {start_date} to {end_date}")

    start = format_entsoe_datetime(start_date)
    end = format_entsoe_datetime(end_date, end=True)
    print(f"🔧 ENTSO-E format: {start} to {end}\n")

    xml_data = fetch_day_ahead_prices(zone, start, end)
    if xml_data is None:
        print("\n⚠️ API fetch failed or no data returned, exiting.")
        exit(1)

    df = parse_prices(xml_data)
    if df.empty:
        print("\n⚠️ No valid data parsed, exiting.")
        exit(1)

    if config.get("normalize_to_kwh", True):
        df = normalize_to_kWh(df)

    df = align_timezones(df)

    print(f"\n📊 Data summary:")
    print(f"   Records: {len(df)}")
    print(f"   Date range: {df['timestamp_local'].min()} to {df['timestamp_local'].max()}")
    print(f"   Price range: €{df['price_EUR_MWh'].min():.2f} - €{df['price_EUR_MWh'].max():.2f} per MWh")

    save_outputs(df, zone, start, end)

    if config.get("make_plots", True):
        plot_prices(df, zone)

    print("\n✅ Processing complete!")
    print("=" * 60)
