import os
import json
import time
import random

import pycountry


from risk_framework.web_api.utils import get_country_wkt

from risk_framework.conf import CACHED_EU_WKT_POLYGONS

OFFICIAL_EU_MEMBERS = [
    'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
    'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
    'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
    'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden'
]
# Get two-digit (alpha_2) codes for official EU members
eu_codes = []
for country_name in OFFICIAL_EU_MEMBERS:
    # Search for the country by name
    country = pycountry.countries.get(name=country_name)
    if not country:
        # Try fuzzy search if exact match fails
        try:
            country = pycountry.countries.search_fuzzy(country_name)[0]
        except (LookupError, IndexError):
            print(f"Warning: Could not find country code for {country_name}")
            continue

    eu_codes.append(country.alpha_2)

european_codes = list(set(eu_codes))
# print(json.dumps(european_codes, indent=4))
# exit()
eu_polygons = {}
if os.path.exists(CACHED_EU_WKT_POLYGONS):
    with open(CACHED_EU_WKT_POLYGONS, 'r') as f:
        eu_polygons = json.load(f)


for country_code in european_codes:
    if country_code not in eu_polygons.keys():
        poly = get_country_wkt(country_code)
        eu_polygons[country_code] = poly
        time.sleep(random.randint(1, 10))
        with open(CACHED_EU_WKT_POLYGONS, 'w') as f:
            json.dump(eu_polygons, f, indent=4)


with open(CACHED_EU_WKT_POLYGONS, 'w') as f:
    json.dump(eu_polygons, f, indent=4)
