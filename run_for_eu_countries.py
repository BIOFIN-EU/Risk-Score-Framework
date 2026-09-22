#!/usr/bin/env python
import time
import requests
import json
import numpy as np

import rasterio
from rasterio.mask import mask
import numpy as np
from shapely import wkt
from shapely.geometry import mapping
import geopandas as gpd
from rasterio.transform import from_origin
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from risk_framework.conf import CACHED_EU_WKT_POLYGONS


API_ENDPOINT = "management-actions/priority/"



def run_single_country(url, country_code):
    print(f"\Running for country code: {country_code}...")
    risk_type = 'Full'

    data = {
        "country_code": country_code,
        'risk_model': 'EddamiriEtAl2026',
        'risk_type': risk_type,
        "sri_logic_type": "fuzzy",
        "sri_correction_method": "HFI",
    }


    start_time = time.perf_counter()
    response = requests.post(url, json=data)
    response.raise_for_status()
    result = response.json()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"\nExecution completed in: {elapsed_time:.4f} seconds")


def run(base_url, country_code):
    # url = f"http://localhost:8030/api/v1/"
    # api gateway
    # url = f"http://localhost:8000/api/vulnerability/management-actions/priority/"
    url = f"{base_url}{API_ENDPOINT}"
    country_list = [country_code]
    if country_code == 'EU_ALL':
        data = None
        with open(CACHED_EU_WKT_POLYGONS, 'r') as f:
            data = json.load(f)
        country_list = data.keys()
    print(f"\Using url: {url}")
    print(f"\Will run for country list: {country_list}.")

    for country_code in country_list:
        run_single_country(url, country_code)



if __name__ == '__main__':
    # run_for_eu_countries.py "http://risk-framework:8030/api/v1/" "NL"

    import sys
    base_url = sys.argv[1]
    country_code = sys.argv[2]
    run(base_url, country_code)
