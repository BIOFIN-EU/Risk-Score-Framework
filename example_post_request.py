import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/predict-future-species-richness-index/"
# url = "http://localhost:8000/api/v1/calculate-current-species-richness-index/"


# Prepare the data
data = {
    "species_name": "Lullula arborea",
    "country_code": "LU",
    "climate_scenario": "ssp245",
    # "climate_scenario": "ssp585",
    "climate_model": "EC-Earth3-Veg",
    "period": "2021-2040",
    # "period": "2041-2060",

    # "wkt_poligon": "POLYGON((34.5 -5.5, 34.5 5.5, 41.5 5.5, 41.5 -5.5, 34.5 -5.5))"  # Optional
}

# Make the POST request
try:
    response = requests.post(url, json=data)
    # Check if request was successful
    response.raise_for_status()

    # Parse and print the JSON response
    result = response.json()
    print(json.dumps(result, indent=2))

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
    result = response.json()
    print(json.dumps(result, indent=2))
except json.JSONDecodeError as e:
    print(f"Error parsing response JSON: {e}")
