import requests
import json
from datetime import datetime, timedelta

# Zone codes
ZONE_CODES = {
    "CY": "10YCY-TSO------Q",
    "GR": "10YGR-HTSO------",
    "DE": "10Y1001A1001A83F",
    "FR": "10YFR-RTE------C",
    "IT": "10YIT-GRTN-----B",
    "ES": "10YES-REE------0",
    "NL": "10YNL----------L",
    "BE": "10YBE----------2",
}

# Load config
with open("config.json") as f:
    config = json.load(f)

API_KEY = config.get("api_token", "")


def test_api_key():
    """Test if API key is valid"""
    print("=" * 70)
    print("🔑 TESTING API KEY VALIDITY")
    print("=" * 70)
    
    url = "https://web-api.tp.entsoe.eu/api"
    
    # Use a simple query that should work for most zones
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    params = {
        "securityToken": API_KEY,
        "documentType": "A44",
        "in_Domain": "10YFR-RTE------C",  # France - usually reliable
        "out_Domain": "10YFR-RTE------C",
        "periodStart": yesterday.strftime("%Y%m%d") + "0000",
        "periodEnd": today.strftime("%Y%m%d") + "0000",
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"📡 Status Code: {r.status_code}")
        print(f"🔗 Test URL: {r.url[:100]}...")
        
        if r.status_code == 200:
            print("✅ API key is valid and working!")
            return True
        elif r.status_code == 401:
            print("❌ API key is INVALID or EXPIRED")
            print("   → Get a new key at: https://transparency.entsoe.eu/")
            return False
        else:
            print(f"⚠️  Unexpected status code: {r.status_code}")
            print(f"Response preview: {r.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_multiple_zones():
    """Test data availability across multiple zones"""
    print("\n" + "=" * 70)
    print("🌍 TESTING MULTIPLE ZONES")
    print("=" * 70)
    
    # Test with a date that should have data (a week ago)
    test_date = datetime.now() - timedelta(days=7)
    start = test_date.strftime("%Y%m%d") + "0000"
    end = (test_date + timedelta(days=1)).strftime("%Y%m%d") + "0000"
    
    print(f"📅 Testing date: {test_date.strftime('%Y-%m-%d')}\n")
    
    url = "https://web-api.tp.entsoe.eu/api"
    results = []
    
    for country, zone in ZONE_CODES.items():
        params = {
            "securityToken": API_KEY,
            "documentType": "A44",
            "in_Domain": zone,
            "out_Domain": zone,
            "periodStart": start,
            "periodEnd": end,
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            has_data = r.status_code == 200 and "<Acknowledgement_MarketDocument" not in r.text
            status = "✅" if has_data else "❌"
            results.append((country, zone, has_data))
            print(f"{status} {country:3} ({zone[:10]}...): {'Data available' if has_data else 'No data'}")
        except Exception as e:
            print(f"⚠️  {country:3}: Error - {str(e)[:50]}")
            results.append((country, zone, False))
    
    # Summary
    available = [c for c, z, h in results if h]
    print(f"\n📊 Summary: {len(available)}/{len(ZONE_CODES)} zones have data")
    
    if available:
        print(f"✅ Zones with data: {', '.join(available)}")
        return available
    else:
        print("❌ No data found in any zone!")
        return []


def test_date_range(zone, country_code):
    """Test a range of dates to find what works"""
    print("\n" + "=" * 70)
    print(f"📅 TESTING DATE RANGE FOR {country_code}")
    print("=" * 70)
    
    url = "https://web-api.tp.entsoe.eu/api"
    today = datetime.now()
    
    test_ranges = [
        ("Today", 0),
        ("Yesterday", 1),
        ("2 days ago", 2),
        ("3 days ago", 3),
        ("1 week ago", 7),
        ("2 weeks ago", 14),
        ("1 month ago", 30),
        ("2 months ago", 60),
        ("3 months ago", 90),
    ]
    
    for label, days_ago in test_ranges:
        test_date = today - timedelta(days=days_ago)
        start = test_date.strftime("%Y%m%d") + "0000"
        end = (test_date + timedelta(days=1)).strftime("%Y%m%d") + "0000"
        
        params = {
            "securityToken": API_KEY,
            "documentType": "A44",
            "in_Domain": zone,
            "out_Domain": zone,
            "periodStart": start,
            "periodEnd": end,
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            has_data = r.status_code == 200 and "<Acknowledgement_MarketDocument" not in r.text
            
            if has_data:
                status = "✅ FOUND"
                print(f"{status} {label:15} ({test_date.strftime('%Y-%m-%d')})")
                return test_date
            else:
                status = "❌"
                print(f"{status} {label:15} ({test_date.strftime('%Y-%m-%d')})")
                
        except Exception as e:
            print(f"⚠️  {label:15}: Error - {str(e)[:50]}")
    
    return None


def detailed_api_response(zone, date):
    """Show detailed API response for debugging"""
    print("\n" + "=" * 70)
    print("🔍 DETAILED API RESPONSE")
    print("=" * 70)
    
    url = "https://web-api.tp.entsoe.eu/api"
    start = date.strftime("%Y%m%d") + "0000"
    end = (date + timedelta(days=1)).strftime("%Y%m%d") + "0000"
    
    params = {
        "securityToken": API_KEY,
        "documentType": "A44",
        "in_Domain": zone,
        "out_Domain": zone,
        "periodStart": start,
        "periodEnd": end,
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"📡 URL: {r.url}")
        print(f"🔑 Status: {r.status_code}")
        print(f"📏 Response size: {len(r.text)} bytes")
        print(f"\n📄 First 1000 characters of response:")
        print("-" * 70)
        print(r.text[:1000])
        print("-" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if not API_KEY:
        print("❌ No API key found in config.json")
        exit(1)
    
    print("\n🔧 ENTSO-E API DIAGNOSTIC TOOL\n")
    print(f"🔑 Using API key: {API_KEY[:20]}...")
    
    # Step 1: Test API key
    if not test_api_key():
        print("\n❌ API key test failed. Please check your API key.")
        exit(1)
    
    # Step 2: Test multiple zones
    available_zones = test_multiple_zones()
    
    if not available_zones:
        print("\n💡 TROUBLESHOOTING SUGGESTIONS:")
        print("   1. Your API key might be new and not yet activated")
        print("   2. There might be temporary API issues")
        print("   3. Check ENTSO-E status: https://transparency.entsoe.eu/")
        print("   4. Try generating a new API key")
        exit(1)
    
    # Step 3: Test date ranges for available zones
    print(f"\n✅ Testing date ranges for available zones...")
    
    for country in available_zones[:3]:  # Test first 3 available
        zone = ZONE_CODES[country]
        found_date = test_date_range(zone, country)
        
        if found_date:
            print(f"\n🎯 SUCCESS! Found data for {country} on {found_date.strftime('%Y-%m-%d')}")
            detailed_api_response(zone, found_date)
            
            print(f"\n📝 RECOMMENDED CONFIG FOR {country}:")
            print("-" * 70)
            safe_start = found_date - timedelta(days=3)
            safe_end = found_date
            print(f"""
{{
  "api_token": "{API_KEY}",
  "country_code": "{country}",
  "start_date": "{safe_start.strftime('%Y-%m-%d')}",
  "end_date": "{safe_end.strftime('%Y-%m-%d')}",
  "normalize_to_kwh": true,
  "export_format": "csv",
  "timezone": "Europe/Berlin",
  "make_plots": true
}}
""")
            break
    
    print("\n✅ Diagnostic complete!")