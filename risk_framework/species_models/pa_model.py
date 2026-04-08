import os
import glob
import numpy as np
import requests
import pycountry

import rasterio
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import box
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import array_bounds
from rasterio.transform import from_origin

from rasterio.mask import mask
from rasterio.features import rasterize
from shapely.geometry import mapping


from risk_framework.conf import PA_PARTS_DATASET_PATH, BASE_RESOLUTION, PA_TEMP_FILE_FORMAT

from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf



class PAModel(object):
    def __init__(self,country_code, wkt_polygon, db):
        self.country_code = country_code
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)

        self.pa_parts_path_regexp = PA_PARTS_DATASET_PATH
        self.temp_pa_path = PA_TEMP_FILE_FORMAT.format(country_code=self.country_code)
        country_dir = os.path.dirname(self.temp_pa_path)
        if not os.path.exists(country_dir):
            os.makedirs(country_dir, exist_ok=True)
        self.db = db

    def load_country_geometries_from_part(self, shp_path, iso3_code):
        print(f'loading {iso3_code} from part {shp_path}')
        gdf_full = gpd.read_file(shp_path, columns=['ISO3'])
        filter_gdf = None
        if iso3_code.upper() not in gdf_full['ISO3'].values:
            print(f"ISO3 '{iso3_code}' NOT found in {shp_path}")
            del gdf_full
        else:
            filter_gdf = gdf_full[gdf_full['ISO3'] == iso3_code.upper()]
        print(f'Done... ')
        return filter_gdf

    def load_country_geometries(self, iso3_code):
        """
        Load country-specific geometries if ISO3 code exists in shapefile.
        Returns GeoDataFrame with country data, or None if not found.
        """
        shapefile_paths = glob.glob(self.pa_parts_path_regexp)
        gdf_country = None
        for i, shp_path in enumerate(shapefile_paths):
            part_gdf = self.load_country_geometries_from_part(shp_path, iso3_code)
            if part_gdf is not None:
                if gdf_country is None:
                    gdf_country = part_gdf
                else:
                    print(f'Concating into maingdf for  {iso3_code}')
                    gdf_country = pd.concat([gdf_country, part_gdf], ignore_index=True)
        return gdf_country

    def get_pa_raster(self):
        iso3_code = pycountry.countries.get(alpha_2=self.country_code).alpha_3

        main_pa_gdf = self.load_country_geometries(iso3_code)
        target_crs = 'EPSG:32632'
        wdpa_proj = main_pa_gdf.to_crs(target_crs)

        total_bounds = wdpa_proj.total_bounds

        # Calculate raster dimensions
        width = int(np.ceil((total_bounds[2] - total_bounds[0]) / BASE_RESOLUTION))
        height = int(np.ceil((total_bounds[3] - total_bounds[1]) / BASE_RESOLUTION))

        print(f"Creating raster: {width} x {height} pixels")

        # Create transform
        transform = from_origin(
            total_bounds[0],
            total_bounds[3],
            BASE_RESOLUTION,
            BASE_RESOLUTION
        )

        # Rasterize geometries
        shapes = [(geom, 1) for geom in wdpa_proj.geometry]
        raster_array = rasterize(
            shapes=shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8
        )


        with rasterio.open(
            self.temp_pa_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=np.uint8,
            crs=target_crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(raster_array, 1)


        with rasterio.open(self.temp_pa_path) as pa_src:
            polygon_gdf = load_poligon_gdf(self.wkt_polygon).to_crs(pa_src.crs)
            bounds = polygon_gdf.total_bounds
            pixel_size_x = abs(pa_src.transform.a)
            pixel_size_y = abs(pa_src.transform.e)
            bbox_margin_x = 10 * pixel_size_x
            bbox_margin_y = 10 * pixel_size_y
            gdf_bbox_emargin = box(
                bounds[0] - bbox_margin_x,
                bounds[1] - bbox_margin_y,
                bounds[2] + bbox_margin_x,
                bounds[3] + bbox_margin_y
            )


            pa_cropped, pa_cropped_transform = mask(
                pa_src,
                [gdf_bbox_emargin],
                crop=True,
                filled=True,
                invert=False,
                nodata=pa_src.nodata
            )

            pa_cropped = pa_cropped[0]

            # Return metadata if needed
            pa_meta = dict(pa_src.profile).copy()
            pa_meta.update({
                'transform': pa_cropped_transform,
                'width': pa_cropped.shape[1],
                'height': pa_cropped.shape[0]
            })

            return pa_cropped, pa_meta

    def clean_up_temp_raster(self):
        if os.path.exists(self.temp_pa_path):
            os.remove(self.temp_pa_path)

    def run(self):
        print('Running CH model.')
        pa_raster, pa_raster_meta = self.get_pa_raster()
        self.clean_up_temp_raster()
        pa_raster_meta['crs'] = str(pa_raster_meta['crs'])
        mean_raster_value = float(np.mean(pa_raster))
        std_raster_value =  float(np.std(pa_raster))
        return {
            "country_code": self.country_code,
            "wkt_polygon": self.wkt_polygon,
            "raster_data": {
                "raster": pa_raster.tolist(),
                "meta": pa_raster_meta,
                'summary_stats': {
                    'mean_raster_value': mean_raster_value,
                    'std_raster_value': std_raster_value,
                },
            },
        }





if __name__ == '__main__':
    import json

    from risk_framework.web_api.utils import get_db
    country_code = 'NL'
    db = list(get_db())[0]



    model = PAModel(country_code, wkt_polygon=None, db=db)

    # model.load_country_geometries(PA_PARTS_DATASET_PATH, 'LUX')
    # model._reproject_pa(PA_PARTS_DATASET_PATH, BASE_RESOLUTION)
    result = model.run()
    raster_value = result['raster_data']['raster']
    raster_meta = result['raster_data']['meta']

    raster = np.array(raster_value, dtype=np.dtype(raster_meta['dtype']))

    print('done, saving...')
    # Write cropped raster to file
    with rasterio.open(
        f'pa_crop_{model.country_code}.tif',
        'w',
        driver='GTiff',
        height=raster_meta['height'],
        width=raster_meta['width'],
        count=1,
        nodata=raster_meta['nodata'],
        dtype=raster_meta['dtype'],
        crs=raster_meta['crs'],
        transform=raster_meta['transform'],
        compress='lzw'
    ) as dst:
        dst.write(raster, 1)

