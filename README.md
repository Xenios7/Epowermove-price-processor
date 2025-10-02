# ⚡ Epowermove Price Processor

A reusable Python script to **download, clean, and process hourly day-ahead electricity price data** from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).  
This project is part of the **ePowerMove** initiative and prepares datasets for optimization and modeling tasks such as EV charging and flexibility analysis.

---

## 🚀 Features
- Fetch hourly **day-ahead wholesale electricity prices** from ENTSO-E (requires API token).  
- Supports multiple European bidding zones.  
- Convert and normalize prices from **€/MWh → €/kWh** (optional).  
- Handle **time zones (UTC + Europe/Nicosia)** with DST awareness.  
- Deal with **missing or irregular hours** (e.g., DST transitions).  
- Export results as **CSV** or **Parquet**.  
- Save **metadata (JSON)**: source, zone code, retrieval date, assumptions.  
- Generate simple **plots** (line chart, heatmap) — can be toggled.  

---

## 📂 Repository Structure
```
Epowermove-price-processor/
│── data/               # processed datasets (output)
│── scripts/            # main processing scripts
│   └── processor.py
│── config.json         # user configuration (API token, country, options)
│── requirements.txt    # Python dependencies
│── README.md           # project documentation
```

---

## ⚙️ Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/Xenios7/Epowermove-price-processor.git
   cd Epowermove-price-processor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Configuration

1. Copy `config.json` and update with your ENTSO-E API token:
   ```json
   {
     "api_token": "YOUR_ENTSOE_API_TOKEN",
     "country_code": "CY",
     "start_date": "2025-09-01",
     "end_date": "2025-09-30",
     "normalize_to_kwh": true,
     "export_format": "csv",
     "timezone": "Europe/Nicosia",
     "make_plots": true
   }
   ```

2. ⚠️ **Never commit your real API token.** Add `config.json` to `.gitignore` and commit only `config_template.json`.

---

## ▶️ Usage

Run the processor:
```bash
python scripts/processor.py
```

Outputs will appear in the `data/` folder:
- `prices_<zone>_<start>_<end>.csv`
- `metadata.json`
- (optional) `plots/` with visualizations

---

## 📊 Example Outputs
- **Line chart** of recent prices (€/kWh vs time).  
- **Heatmap** of average daily prices across hours.  

---

## 📜 License
MIT License — free to use, modify, and share.
