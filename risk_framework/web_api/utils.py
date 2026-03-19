import uuid
from typing import Optional, List

from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.transform import from_origin
from rasterio.warp import reproject, calculate_default_transform
from shapely import wkt
from shapely.geometry import mapping
from shapely.geometry import shape
import geopandas as gpd
import numpy as np
import rasterio

import requests

from risk_framework.conf import SessionLocal, NOMINATIM_API


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_geo_uuid(country_code: str, wkt_polygon: Optional[str] = None) -> str:
    """
    Generate a deterministic UUID based on input parameters.
    Uses empty string for optional wkt_polygon if not provided.
    """
    # Use empty string if wkt_polygon is None
    polygon_str = wkt_polygon if wkt_polygon else ""

    # Create a string combining all parameters
    keys_list = [country_code, polygon_str]
    input_keys_strign = '_'.join(keys_list)

    namespace = uuid.NAMESPACE_DNS
    cache_uuid = str(uuid.uuid5(namespace, input_keys_strign))

    return cache_uuid


def get_country_wkt(country_code):
    params = {
        'country': country_code,
        'countrycodes': country_code,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 1,
        'featuretype': 'country'
    }
    headers = {'User-Agent': 'MyApp/1.0'}

    response = requests.get(NOMINATIM_API, params=params, headers=headers)
    data = response.json()[0]
    geometry = shape(data['geojson'])
    return geometry.wkt

def load_poligon_gdf(wkt_polygon):
    geometry = wkt.loads(wkt_polygon)
    polygon_gdf = gpd.GeoDataFrame({'geometry': [geometry]}, crs='EPSG:4326')
    return polygon_gdf


def apply_geometry_mask_to_raster(wkt_polygon, raster_array, raster_meta, crop=False, nodata=-1):
    cliped_raster_meta = raster_meta.copy()
    polygon_gdf = load_poligon_gdf(wkt_polygon)


    # Create transform object for rasterio
    transform = from_origin(
        cliped_raster_meta['transform'][2],  # top-left x
        cliped_raster_meta['transform'][5],  # top-left y
        cliped_raster_meta['transform'][0],  # pixel width
        abs(cliped_raster_meta['transform'][4])  # pixel height (make positive)
    )
    cliped_raster_meta['nodata'] = nodata
    # Create in-memory dataset and mask
    with MemoryFile() as memfile:
        with memfile.open(
            driver='GTiff',
            height=raster_meta['height'],
            width=raster_meta['width'],
            count=1,
            dtype=raster_array.dtype,
            crs=raster_meta['crs'],
            transform=transform
        ) as dataset:

            # Write data
            dataset.write(raster_array, 1)

            # Ensure polygon is in same CRS as raster
            if polygon_gdf.crs != dataset.crs:
                polygon_gdf = polygon_gdf.to_crs(dataset.crs)

            # Apply mask
            geoms = [mapping(polygon_gdf.geometry.values[0])]
            mask_array, out_transform = mask(
                dataset,
                geoms,
                crop=False,
                filled=True,
                invert=False,
                nodata=nodata
            )
            masked_raster = np.where(mask_array[0] == 1, raster_array, -1)# Check pixels that are NOT -1 in masked_result
            masked_result = mask_array[0]
            valid_pixels = masked_result != -1

            # Compare original vs masked where mask has valid values
            if np.any(valid_pixels):
                are_equal = np.allclose(raster_array[valid_pixels], masked_result[valid_pixels])
                print(f"Original and masked values match inside polygon: {are_equal}")

                if not are_equal:
                    diff = np.abs(raster_array[valid_pixels] - masked_result[valid_pixels])
                    print(f"Max difference: {np.max(diff)}")
                    print(f"Mean difference: {np.mean(diff)}")
            else:
                print("No valid pixels found inside polygon")
            return mask_array[0]

def reproject_to_crs(rasterio_src, dst_crs='EPSG:4326'):
    # Calculate transform for EPSG:4326
    transform, width, height = calculate_default_transform(
        rasterio_src.crs, dst_crs, rasterio_src.width, rasterio_src.height, *rasterio_src.bounds
    )

    # Create destination array
    destination = np.zeros((height, width), dtype=rasterio_src.dtypes[0])

    # Reproject
    reproject(
        source=rasterio.band(rasterio_src, 1),
        destination=destination,
        src_transform=rasterio_src.transform,
        src_crs=rasterio_src.crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear
    )

    metadata = rasterio_src.profile.copy()
    metadata.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height
    })
    return destination, metadata

# def clip_to_wkt_polygon(wkt_polygon, raster_value, raster_meta):
#     gdf = load_poligon_gdf(wkt_polygon)
#     clipped_raster, clipped_transform = mask(raster_value, gdf.geometry, crop=True)
#     out_meta = raster_meta.copy()

#     # Update metadata of clipped raster
#     out_meta.update({
#         "driver": "GTiff",
#         "height": out_image.shape[1],
#         "width": out_image.shape[2],
#         "transform": out_transform
#     })
