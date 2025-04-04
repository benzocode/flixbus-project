from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from flixbus_trip_search import find_cheapest_trips
import os
from datetime import datetime, timedelta
import pytz  # For handling timezones
from dateutil import parser
import re


# Set the timezone (adjust this based on your use case)
local_tz = pytz.timezone('Europe/Amsterdam')  # Or use your local timezone

def parse_duration(duration_str):
    """Extract hours and minutes from a string like '9h 30m'."""
    hours, minutes = 0, 0
    match = re.match(r"(\d+)h (\d+)m", duration_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
    return hours, minutes

def format_times(raw_departure, duration_str):
    # Clean raw_departure to remove non-ASCII characters
    raw_departure_clean = re.sub(r'^[A-Za-z]+, ', '', raw_departure)  # Remove weekday name (e.g., 'Sat, ')
    raw_departure_clean = re.sub(r' — ', 'T', raw_departure_clean)  # Change the dash to a 'T' for ISO format
    raw_departure_clean = re.sub(r'\s+', ' ', raw_departure_clean)  # Replace multiple spaces with a single space
    
    # Parse the cleaned departure time
    try:
        dt = parser.parse(raw_departure_clean)
    except ValueError as e:
        print(f"Error parsing departure time: {raw_departure_clean} - {e}")
        raise

    # Localize the departure time to your desired timezone
    dt_localized = dt.astimezone(local_tz)

    # Format the departure time
    departure_time = dt_localized.strftime("%a, %b %d — %I:%M %p")

    # Parse duration string (e.g., '9h 30m')
    hours, minutes = parse_duration(duration_str)

    # Calculate arrival time
    arrival_dt = dt_localized + timedelta(hours=hours, minutes=minutes)

    # Format the arrival time
    arrival_time = arrival_dt.strftime("%a, %b %d — %I:%M %p")
    
    return departure_time, arrival_time


os.chdir('/Users/benstein/Desktop/Python')

app = FastAPI()

class TripSearchRequest(BaseModel):
    from_city: str
    to_city: str
    start_date: str  # in format YYYY-MM-DD
    end_date: str    # in format YYYY-MM-DD

@app.post("/search")
def search_trips(request: TripSearchRequest):
    print(f"Received request: {request}")  # Print the incoming request for debugging

    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    trips = find_cheapest_trips(
        from_city=request.from_city,
        to_city=request.to_city,
        start_date=start_date,
        end_date=end_date
    )

    if not trips:
        raise HTTPException(status_code=404, detail="No trips found.")

    # Find the cheapest trip based on price
    cheapest_trip = min(trips, key=lambda trip: trip['Price (USD)'])

    # Format times using the helper function
    departure_time, arrival_time = format_times(cheapest_trip["Departure Time"], cheapest_trip["Duration"])

    # Return the cheapest trip with correct times
    return {
        "cheapest_trip": {
            "Date": cheapest_trip["Date"],
            "Price (USD)": cheapest_trip["Price (USD)"],
            "Departure Time": departure_time,
            "Arrival Time": arrival_time,
            "Duration": cheapest_trip["Duration"]
        }
    }


