#!/usr/bin/env python3
"""Display current weather in Potsdam on the LED badge using WeatherAPI.com"""

import requests
from lednamebadge import SimpleTextAndIcons, LedNameBadge
from array import array
import json
import sys

# WeatherAPI.com configuration - You'll need to get your own API key from https://www.weatherapi.com/
WEATHER_API_KEY = "a5da6ef1a5814bbea7c162012240703"  # Replace with your actual API key
WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"
LOCATION = "Potsdam,Germany"

def get_weather_data():
    """Fetch current weather data from WeatherAPI.com"""
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': LOCATION,
            'aqi': 'no'  # We don't need air quality data for the badge
        }
        
        print(f"Fetching weather data for {LOCATION}...")
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        
        weather_data = response.json()
        return weather_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing weather data: {e}")
        return None

def format_weather_message(weather_data):
    """Format weather data into a message suitable for the LED badge"""
    if not weather_data:
        return "Weather unavailable"
    
    try:
        current = weather_data['current']
        location = weather_data['location']
        
        # Extract key information
        city = location['name']
        temp_c = current['temp_c']
        condition = current['condition']['text']
        
        # Create a concise message for the LED badge
        # Format: "Potsdam: 15°C Sunny"
        message = f"{city}: {temp_c:.0f}°C {condition}"
        
        print(f"Weather message: {message}")
        return message
        
    except KeyError as e:
        print(f"Error parsing weather data structure: {e}")
        return "Weather format error"

def display_weather_on_led():
    """Main function to fetch weather and display on LED badge"""
    
    # Check if API key is configured
    if WEATHER_API_KEY == "YOUR_API_KEY_HERE":
        print("Error: Please set your WeatherAPI.com API key in the script")
        print("Get your free API key from: https://www.weatherapi.com/")
        sys.exit(1)
    
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
            speeds=[3],        # Scroll speed (1-8) - slightly slower than hello world
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
    else:
        print("Could not fetch weather data")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--info':
        # Print detailed weather info to console
        print_weather_info()
    else:
        # Display weather on LED badge
        display_weather_on_led()