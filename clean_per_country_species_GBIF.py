import json
import time
import random
import requests
from risk_framework.species_models.per_country_species_conf import INDICATOR_SP_PER_COUNTRY

GBIF_API_BASE ="https://api.gbif.org/v1/occurrence/search"
def get_gbif_species_data(species_name, country_code):
    print(f'Getting info about {species_name}..')
    has_species = False
    try:
        params = {"scientificName":species_name,"country":country_code,
                "hasCoordinate":"true","basisOfRecord":"HUMAN_OBSERVATION","limit":10000}
        r = requests.get(GBIF_API_BASE, params=params); r.raise_for_status()
        data = r.json().get("results", [])
        has_species = len(data) > 0
    except Exception as e:
        print(f'Exception during request for {species_name}: {e}')

    return has_species


bad_country_species = {}

cleaned_dict = {}
for country_code, species_list in INDICATOR_SP_PER_COUNTRY.items():
    cleaned_dict[country_code] = []
    bad_country_species[country_code] = []
    for species_name in species_list:
        has_species = get_gbif_species_data(species_name)
        time.sleep(random.randint(0, 5))
        if has_species:
            cleaned_dict[country_code].append(species_name)
        else:
            bad_country_species[country_code].append(species_name)

with open('cleaned_species.json', 'w') as f:
    json.dump(cleaned_dict, f, indent=4)

with open('bad_species.json', 'w') as f:
    json.dump(cleaned_dict, f, indent=4)

# with open('cleaned_species.json', 'r') as f:
#     cleaned_dict = json.load(f)

# for country_code, species_list in cleaned_dict.items():
#     for species_name in species_list:
#         existing_species.add(species_name)

# for country_code, species_list in INDICATOR_SP_PER_COUNTRY.items():
#     for species_name in species_list:
#         if species_name not in existing_species:
#             bad_species.add(species_name)

# with open('bad_species.json', 'w') as f:
#     json.dump(list(bad_species), f, indent=4)

