#!/usr/bin/env python
import requests


from .per_country_species_conf import INDICATOR_SP_PER_COUNTRY


url = "http://localhost:8000/api/v1/calculate-current-species-richness-index/"


def run_for_contry(country_code, species_list):
    for species in species_list:

        data = {
            "species_name": species,
            "country_code": country_code,
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




if __name__ == '__main__':
    pass
