#!/usr/bin/env python3
"""Display current weather in Potsdam on the LED badge using OpenMeteo API (no API key required)"""

import requests
from lednamebadge import SimpleTextAndIcons, LedNameBadge
from array import array
import json
import sys

# OpenMeteo API configuration (free, no API key required)
WEATHER_API_URL = "https://api.open-meteo.com/v1/current"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"

def get_coordinates(city="Potsdam"):
    """Get coordinates for the city"""
    try:
        params = {
            'name': city,
            'count': 1,
            'language': 'en',
            'format': 'json'
        }
        
        print(f"Getting coordinates for {city}...")
        response = requests.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('results'):
            result = data['results'][0]
            return result['latitude'], result['longitude'], result['name']
        else:
            print(f"Could not find coordinates for {city}")
            return None, None, city
        
    except Exception as e:
        print(f"Error getting coordinates: {e}")
        return None, None, city

def get_weather_data():
    """Fetch current weather data from OpenMeteo API"""
    try:
        # Get coordinates for Potsdam
        lat, lon, city_name = get_coordinates("Potsdam")
        
        if lat is None or lon is None:
            # Fallback to Potsdam coordinates
            lat, lon = 52.3988, 13.0656
            city_name = "Potsdam"
        
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
            'timezone': 'Europe/Berlin'
        }
        
        print(f"Fetching weather data for {city_name}...")
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        
        weather_data = response.json()
        weather_data['city_name'] = city_name  # Add city name to the data
        return weather_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing weather data: {e}")
        return None

def get_weather_condition_text(weather_code):
    """Convert weather code to readable text"""
    weather_conditions = {
        0: "Clear",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing Rime Fog",
        51: "Light Drizzle",
        53: "Moderate Drizzle",
        55: "Dense Drizzle",
        56: "Light Freezing Drizzle",
        57: "Dense Freezing Drizzle",
        61: "Slight Rain",
        63: "Moderate Rain",
        65: "Heavy Rain",
        66: "Light Freezing Rain",
        67: "Heavy Freezing Rain",
        71: "Slight Snow",
        73: "Moderate Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Slight Rain Showers",
        81: "Moderate Rain Showers",
        82: "Violent Rain Showers",
        85: "Slight Snow Showers",
        86: "Heavy Snow Showers",
        95: "Thunderstorm",
        96: "Thunderstorm Light Hail",
        99: "Thunderstorm Heavy Hail"
    }
    return weather_conditions.get(weather_code, "Unknown")

def format_weather_message(weather_data):
    """Format weather data into a message suitable for the LED badge"""
    if not weather_data:
        return "Weather unavailable"
    
    try:
        current = weather_data['current']
        city_name = weather_data.get('city_name', 'Potsdam')
        
        # Extract key information
        temp_c = current['temperature_2m']
        weather_code = current['weather_code']
        condition = get_weather_condition_text(weather_code)
        
        # Create a concise message for the LED badge
        # Format: "Potsdam: 15°C Clear"
        message = f"{city_name}: {temp_c:.0f}°C {condition}"
        
        print(f"Weather message: {message}")
        return message
        
    except KeyError as e:
        print(f"Error parsing weather data structure: {e}")
        return "Weather format error"

def display_weather_on_led():
    """Main function to fetch weather and display on LED badge"""
    
    # Fetch weather data
    weather_data = get_weather_data()
    
    # Format the message
    message = format_weather_message(weather_data)
    
    # Display on LED badge
    try:
        print("Displaying weather on LED badge...")
        
        # Create text processor
        creator = SimpleTextAndIcons()
        
        # Create bitmap for weather message
        scene_bitmap = creator.bitmap(message)
        
        # Create the buffer with protocol header
        buf = array('B')
        buf.extend(LedNameBadge.header(
            lengths=[scene_bitmap[1]], 
            speeds=[3],        # Scroll speed (1-8) - slightly slower for readability
            modes=[0],         # Scroll left mode
            blinks=[0],        # No blinking
            ants=[0],          # No animated border
            brightness=100     # 100% brightness
        ))
        
        # Add the bitmap data
        buf.extend(scene_bitmap[0])
        
        # Write to the LED badge
        LedNameBadge.write(buf)
        
        print(f"Successfully sent weather data to LED badge: {message}")
        
    except Exception as e:
        print(f"Error displaying on LED badge: {e}")
        sys.exit(1)

def print_weather_info():
    """Print detailed weather information to console"""
    weather_data = get_weather_data()
    
    if weather_data:
        print("\n=== Detailed Weather Information ===")
        print(json.dumps(weather_data, indent=2))
        
        # Also print human-readable format
        if 'current' in weather_data:
            current = weather_data['current']
            city_name = weather_data.get('city_name', 'Potsdam')
            temp = current.get('temperature_2m', 'N/A')
            humidity = current.get('relative_humidity_2m', 'N/A')
            wind_speed = current.get('wind_speed_10m', 'N/A')
            weather_code = current.get('weather_code', 0)
            condition = get_weather_condition_text(weather_code)
            
            print(f"\n=== Human Readable Summary ===")
            print(f"Location: {city_name}")
            print(f"Temperature: {temp}°C")
            print(f"Condition: {condition}")
            print(f"Humidity: {humidity}%")
            print(f"Wind Speed: {wind_speed} km/h")
    else:
        print("Could not fetch weather data")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--info':
        # Print detailed weather info to console
        print_weather_info()
    else:
        # Display weather on LED badge
        display_weather_on_led()