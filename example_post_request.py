
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

# API endpoint
# url = "http://localhost:8000/api/v1/predict-future-habitat-suitability/"
url = "http://localhost:8000/api/v1/calculate-current-habitat-suitability/"

# each raster need to have their own meta... they are all different u.u....

wkt_polygon = """
POLYGON((6.002283447287779 50.1760789292249,5.911989337734383 50.10892346308722,5.74541965173361 49.90016959719293,5.782827000600723 49.78649344075785,5.874537719815358 49.7041329152033,5.888969430739237 49.61888233727015,5.813653017083325 49.55299367066908,5.8445970843710295 49.50305212079425,5.972269030090262 49.48589567091915,6.005042884857068 49.441358513874576,6.154318127910205 49.492052387973075,6.2630429194103545 49.508718555081174,6.368727902679095 49.46146224747113,6.3786736830090485 49.5513297742786,6.440429010428717 49.67626997911219,6.520334649133021 49.71489429636492,6.516557023369716 49.813494212706615,6.346858991033706 49.851876347443465,6.2227285694675745 49.900672793310406,6.207736117219453 49.95315673182682,6.123492111427604 50.050713296650514,6.142380240244133 50.15210498234012,6.002283447287779 50.1760789292249))
"""



wkt_polygon = """
POLYGON((6.221110073743708 49.78007047228277,6.203365196590148 49.73459984424554,6.296590013756872 49.740444947385186,6.335201035001955 49.77807805368181,6.221110073743708 49.78007047228277))
"""

# Prepare the data
data = {
    "species": "Lullula arborea",
    # "species": "Accipiter nisus",
    # "species": "Aegithalos caudatus",

    # "species": "Streptopelia turtur",
    # "country_code": "LU",
    "country_code": "NL",
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


# with open('your_raster.json', 'w') as f:
#     json.dump(result, f)


# result = None
# with open('your_raster.json', 'r') as f:
#     result = json.load(f)

# luxembourg_polygon = wkt.loads(wkt_polygon)

# print(f"Polygon bounds: {luxembourg_polygon.bounds}")
# print(f"Polygon area (approx degrees²): {luxembourg_polygon.area}")

# # =====================================================
# # 3. APPLY MASK TO RASTER
# # =====================================================
# # Your metadata
# # meta = {
# #     "driver": "GTiff",
# #     "dtype": "float32",
# #     "nodata": None,
# #     "width": 233,
# #     "height": 170,
# #     "count": 1,
# #     "crs": "EPSG:4326",  # Simplified from your WKT
# #     "transform": [
# #         0.008333333333333338,  # pixel width
# #         0.0,
# #         5.150000000000119,      # top-left x
# #         0.0,
# #         -0.008333333333333338,  # pixel height (negative)
# #         50.38333333333331,       # top-left y
# #         0.0, 0.0, 1.0
# #     ]
# # }
# meta = result['meta']

# # Your raster data (2D array from JSON)
# raster_grid = result['raster_data']['raster']  # This is a 2D list/array
# raster_array = np.array(raster_grid, dtype=np.float32)

# # Create transform object for rasterio
# transform = from_origin(
#     meta['transform'][2],  # top-left x
#     meta['transform'][5],  # top-left y
#     meta['transform'][0],  # pixel width
#     # abs(meta['transform'][4])  # pixel height (make positive)
#     abs(meta['transform'][4])  # pixel height (make positive)
# )

# # Convert WKT to polygon
# lux_polygon = wkt.loads(wkt_polygon)
# polygon_gdf = gpd.GeoDataFrame({'geometry': [lux_polygon]}, crs='EPSG:4326')

# # Create in-memory dataset and mask
# with MemoryFile() as memfile:
#     with memfile.open(
#         driver='GTiff',
#         height=meta['height'],
#         width=meta['width'],
#         count=1,
#         dtype=raster_array.dtype,
#         crs=meta['crs'],
#         transform=transform
#     ) as dataset:

#         # Write data
#         dataset.write(raster_array, 1)

#         # Ensure polygon is in same CRS as raster
#         if polygon_gdf.crs != dataset.crs:
#             polygon_gdf = polygon_gdf.to_crs(dataset.crs)

#         # Apply mask
#         geoms = [mapping(polygon_gdf.geometry.values[0])]
#         out_image, out_transform = mask(
#             dataset,
#             geoms,
#             crop=False,
#             filled=True,
#             invert=False,
#             nodata=-1  # Temporary mask value outside 0-1 range
#         )

#         # =====================================================
#         # 4. RESULT# =====================================================
#         print(f"Original raster shape: {raster_array.shape}")
#         print(f"Masked result shape: {out_image.shape}")

#         # For NaN, use np.isnan() not ==
#         inside_mask = ~np.isnan(out_image)  # True where NOT NaN
#         outside_mask = np.isnan(out_image)   # True where IS NaN

#         print(f"Values inside polygon (0-1): {out_image[inside_mask][:10]}")  # First 10 inside values
#         print(f"Outside value: NaN")
#         print(f"Number of pixels inside: {np.sum(inside_mask)}")
#         print(f"Number of pixels outside: {np.sum(outside_mask)}")


# import ipdb; ipdb.set_trace()
# # Extract data
meta = result['raster_data']['meta']
dtype = meta['dtype']
# dtype = 'float64'
# predictor = meta['predictor']
compress = meta['compress']
raster_value = result['raster_data']['raster']
# raster_value = out_image[0]  # Remove the band dimension
raster = np.array(raster_value, dtype=np.dtype(dtype))

rasterio_kwargs = meta
# # Save as GeoTIFF - rasterio handles the transform directly
with rasterio.open(
    'probability_raster.tif',
    'w',
    driver='GTiff',
    height=raster.shape[0],
    width=raster.shape[1],
    count=1,
    dtype=dtype,
    crs=meta['crs'],
    transform=meta['transform'],  # rasterio accepts the affine directly
    nodata=-1
) as dst:
    dst.write(raster, 1)

# with rasterio.open(
#     'probability_raster.tif',
#     'w',
#     **rasterio_kwargs
# ) as dst:
#     dst.write(raster, 1)





