import requests
import datetime
import pandas as pd
from time import sleep
from dateutil import parser
from datetime import timedelta
import os
from concurrent.futures import ThreadPoolExecutor


os.chdir('/Users/benstein/Desktop/Python')

# --- API URL and Params ---
base_url = "https://global.api.flixbus.com/search/service/v4/search"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://shop.flixbus.com",
    "Referer": "https://shop.flixbus.com/"
}

def get_city_id_by_name(city_name):
    url = "https://global.api.flixbus.com/search/autocomplete/cities"
    params = {
        "q": city_name,
        "lang": "en_US",
        "country": "us",
        "flixbus_cities_only": "false",
        "is_train_only": "false",
        "stations": "true",
        "popular_stations": "true",
        "popular_stations_count": "null"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        cities = response.json()

        if not cities:
            print(f"❌ No match found for: {city_name}")
            return None

        top_result = cities[0]
        print(f"✅ Matched '{city_name}' to '{top_result['name']}' (ID: {top_result['id']})")
        return top_result["id"]

    except Exception as e:
        print(f"❌ Error fetching city ID for {city_name}: {e}")
        return None

def get_trip_details_for_date(date_str, from_city_id, to_city_id):
    params = {
        "from_city_id": from_city_id,
        "to_city_id": to_city_id,
        "departure_date": date_str,
        "products": '{"adult":1}',
        "currency": "USD",
        "locale": "en_US",
        "search_by": "cities",
        "include_after_midnight_rides": "1",
        "disable_distribusion_trips": "0",
        "disable_global_trips": "0"
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
        trips = data.get("trips", [])

        if not trips:
            return None

        best_trip = None
        min_price = float('inf')

        for trip in trips:
            results = trip.get("results", {})
            for option in results.values():
                price = option.get("price", {}).get("total_with_platform_fee")
                raw_departure = option.get("departure", {}).get("date")
                duration_data = option.get("duration", {})

                if raw_departure and duration_data:
                    dt = parser.isoparse(raw_departure)
                    hours = duration_data.get("hours", 0)
                    minutes = duration_data.get("minutes", 0)
                    departure_time = dt.strftime("%a, %b %d — %I:%M %p")
                    duration = f"{hours}h {minutes}m"
                    arrival_dt = dt + timedelta(hours=hours, minutes=minutes)
                    arrival_time = arrival_dt.strftime("%a, %b %d — %I:%M %p")
                else:
                    departure_time = "N/A"
                    arrival_time = "N/A"
                    duration = "N/A"

                if price is not None and price > 0 and price < min_price:
                    min_price = price
                    best_trip = {
                        "Date": date_str,
                        "Price (USD)": price,
                        "Departure Time": departure_time,
                        "Arrival Time": arrival_time,
                        "Duration": duration
                    }

        return best_trip

    except Exception as e:
        print(f"❌ Error on {date_str}: {e}")
        return None

def find_cheapest_trips(from_city, to_city, start_date, end_date):
    from_city_id = get_city_id_by_name(from_city)
    to_city_id = get_city_id_by_name(to_city)

    if not from_city_id or not to_city_id:
        return {"error": "Invalid city name(s)."}

    def fetch_trip_for_date(date):
        date_str = date.strftime("%d.%m.%Y")
        trip_info = get_trip_details_for_date(date_str, from_city_id, to_city_id)
        if trip_info:
            print(f"{date_str} → ${trip_info['Price (USD)']} | {trip_info['Departure Time']} → {trip_info['Arrival Time']} | {trip_info['Duration']}")
        else:
            print(f"{date_str} → No trips found")
        return trip_info

    # Generate list of dates
    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]

    # Run in parallel using 20 threads
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_trip_for_date, date_list))

    # Filter out None values (no trips)
    return [trip for trip in results if trip]


# Example usage
if __name__ == "__main__":
    from_city = "Groningen"
    to_city = "Berlin"
    start_date = datetime.date(2025, 4, 1)
    end_date = datetime.date(2025, 5, 31)

    results = find_cheapest_trips(from_city, to_city, start_date, end_date)
    df = pd.DataFrame(results).dropna().sort_values(by="Price (USD)")
    print("\nCheapest Day in Date Range:")
    print(df.head(1).to_string(index=False))
