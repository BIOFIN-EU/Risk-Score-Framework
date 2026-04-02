
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

raster_name = 'risk'
prediction_type = 'current'
# prediction_type = 'future'

url = f"http://localhost:8000/api/v1/{raster_name}/{prediction_type}/"


# # each raster need to have their own meta... they are all different u.u....

# wkt_polygon = """
# POLYGON((6.002283447287779 50.1760789292249,5.911989337734383 50.10892346308722,5.74541965173361 49.90016959719293,5.782827000600723 49.78649344075785,5.874537719815358 49.7041329152033,5.888969430739237 49.61888233727015,5.813653017083325 49.55299367066908,5.8445970843710295 49.50305212079425,5.972269030090262 49.48589567091915,6.005042884857068 49.441358513874576,6.154318127910205 49.492052387973075,6.2630429194103545 49.508718555081174,6.368727902679095 49.46146224747113,6.3786736830090485 49.5513297742786,6.440429010428717 49.67626997911219,6.520334649133021 49.71489429636492,6.516557023369716 49.813494212706615,6.346858991033706 49.851876347443465,6.2227285694675745 49.900672793310406,6.207736117219453 49.95315673182682,6.123492111427604 50.050713296650514,6.142380240244133 50.15210498234012,6.002283447287779 50.1760789292249))
# """




# Risk:

data = {
    # "country_code": "LU",
    "country_code": "NL",
    'risk_model': 'PontesEtAl2026',
    'crop_to_polygon': True,

    "sri_logic_type": "fuzzy",
    "sri_correction_method": "HFI",
    'sri_override_species_list': "Accipiter nisus,Aegithalos caudatus"
    # "climate_scenario": "ssp245",
    # "climate_scenario": "ssp585",
    # "climate_model": "EC-Earth3-Veg",
    # "period": "2021-2040",
    # "period": "2041-2060",

    # "wkt_polygon": wkt_polygon
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

except Exception:
    exit




for raster_key, raster_group in [('raster_data', 'green'), ('raster_data_urban', 'urban'), ('xai_raster', 'xai')]:

    meta = result[raster_key]['meta']
    dtype = meta['dtype']
    # dtype = 'float64'
    # predictor = meta['predictor']
    # compress = meta['compress']
    raster_value = result[raster_key]['raster']
    # raster_value = out_image[0]  # Remove the band dimension
    raster = np.array(raster_value, dtype=np.dtype(dtype))

    rasterio_kwargs = meta
    # # Save as GeoTIFF - rasterio handles the transform directly
    with rasterio.open(
        f'raster_{raster_name}_{prediction_type}_{raster_group}.tif',
        'w',
        driver='GTiff',
        height=raster.shape[0],
        width=raster.shape[1],
        count=1,
        dtype=dtype,
        crs=meta['crs'],
        transform=meta['transform'],  # rasterio accepts the affine directly
        nodata=meta['nodata']
    ) as dst:
        dst.write(raster, 1)

# with rasterio.open(
#     'probability_raster.tif',
#     'w',
#     **rasterio_kwargs
# ) as dst:
#     dst.write(raster, 1)


# print(json.dumps(result['xai_summary']))
# print(json.dumps(result['risk_ling_thresholds']))


import ipdb; ipdb.set_trace()
