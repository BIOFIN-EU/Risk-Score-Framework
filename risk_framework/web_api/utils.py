import os
import json
import uuid
from typing import Optional, List

from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.transform import from_origin
from rasterio.warp import reproject, calculate_default_transform
from shapely import wkt , MultiPolygon
from shapely.geometry import mapping
from shapely.geometry import shape ,Point
import geopandas as gpd
import numpy as np
import rasterio

import requests

from risk_framework.conf import SessionLocal, NOMINATIM_API, NOMINATIM_REVERSE_API, CACHED_EU_WKT_POLYGONS


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
    if os.path.exists(CACHED_EU_WKT_POLYGONS):
        with open(CACHED_EU_WKT_POLYGONS, 'r') as f:
            cached_polygons = json.load(f)
            wkt_pol = cached_polygons.get(country_code)
            if wkt_pol is not None:
                return wkt_pol
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
    centroid = Point(float(data['lon']), float(data['lat']))
    geometry = shape(data['geojson'])
    valid_polygons = []
    if geometry.geom_type == 'MultiPolygon':
        # add valid polygons from list of polygons that contain centroid or have their centroid X km from the centroid.
        geoms = list(geometry.geoms)
        for poly in geoms:
            poly_centroid = poly.centroid
            if poly.contains(centroid):
                valid_polygons.append(poly)
            else:
                # approx
                distance_km = centroid.distance(poly_centroid) * 111
                if distance_km < 750:
                    valid_polygons.append(poly)
        geometry = MultiPolygon(valid_polygons)

    return geometry.wkt


def load_poligon_gdf(wkt_polygon):
    geometry = wkt.loads(wkt_polygon)
    polygon_gdf = gpd.GeoDataFrame({'geometry': [geometry]}, crs='EPSG:4326')
    return polygon_gdf


def apply_geometry_mask_to_raster(polygon_gdf, raster_array, raster_meta, crop=False, nodata=-9999.0):
    cliped_raster_meta = dict(raster_meta.copy())


    # Create transform object for rasterio
    transform = from_origin(
        cliped_raster_meta['transform'][2],  # top-left x
        cliped_raster_meta['transform'][5],  # top-left y
        cliped_raster_meta['transform'][0],  # pixel width
        abs(cliped_raster_meta['transform'][4])  # pixel height (make positive)
    )
    # Create in-memory dataset and mask
    with MemoryFile() as memfile:
        with memfile.open(
            driver='GTiff',
            height=raster_meta['height'],
            width=raster_meta['width'],
            count=1,
            dtype=raster_array.dtype,
            crs=raster_meta['crs'],
            nodata=raster_meta['nodata'],
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
                crop=crop,
                all_touched=True,
                filled=True,
                invert=False,
                nodata=nodata
            )
            final_raster = mask_array[0]
            cliped_raster_meta.update({
                'transform': out_transform,
                'width': final_raster.shape[1],
                'height': final_raster.shape[0]
            })
            return final_raster, cliped_raster_meta

def reproject_to_crs(rasterio_src, dst_crs='EPSG:4326', dst_nodata=None, dst_dtype=None, resampling=Resampling.bilinear):
    # Calculate transform for EPSG:4326
    transform, width, height = calculate_default_transform(
        rasterio_src.crs, dst_crs, rasterio_src.width, rasterio_src.height, *rasterio_src.bounds
    )

    if dst_dtype is None:
        dst_dtype = rasterio_src.dtypes[0]

    # Create destination array
    destination = np.zeros((height, width), dtype=dst_dtype)

    if dst_nodata is None:
        dst_nodata = rasterio_src.nodata

    # Reproject
    reproject(
        source=rasterio.band(rasterio_src, 1),
        destination=destination,
        src_transform=rasterio_src.transform,
        src_crs=rasterio_src.crs,
        src_nodata=rasterio_src.nodata,
        dst_transform=transform,
        dst_crs=dst_crs,
        dst_nodata=dst_nodata,
        resampling=resampling
    )

    metadata = rasterio_src.profile.copy()
    metadata.update({
        'crs': dst_crs,
        'nodata': dst_nodata,
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
