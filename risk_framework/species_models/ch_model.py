import numpy as np
import requests

import rasterio
import geopandas as gpd
from shapely import wkt
from shapely.geometry import box
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import array_bounds
from rasterio.transform import from_origin

from rasterio.mask import mask
from shapely.geometry import mapping


from risk_framework.conf import CH_DATASET_PATH, CH_REPROJ_DATASET_PATH

from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf, reproject_to_crs



class CHModel(object):
    def __init__(self,country_code, wkt_polygon, db):
        self.country_code = country_code
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)

        self.ch_raster_path = CH_REPROJ_DATASET_PATH
        self.final_nodata = -9999
        self.db = db

    def _reproject_ch(self, ch_origin_path):
        print('Loading CH Full dataset...')
        with rasterio.open(ch_origin_path) as ch_src:
            dst_crs='EPSG:4326'
            dst_dtype = np.float32
            print('Reprojecting CH Full dataset...')
            ch_raster_rep, ch_rep_meta = reproject_to_crs(ch_src, dst_crs, dst_nodata=self.final_nodata, dst_dtype=dst_dtype)
            print('Reprojecting CH Full dataset... Done.')

            with rasterio.open(
                self.ch_raster_path,
                'w',
                driver='GTiff',
                height=ch_raster_rep.shape[0],
                width=ch_raster_rep.shape[1],
                nodata=ch_rep_meta['nodata'],
                count=1,
                dtype=dst_dtype,
                crs=ch_rep_meta['crs'],
                transform=ch_rep_meta['transform'],
            ) as dst:
                dst.write(ch_raster_rep, 1)

    def transform_ch_to_index(self, ch_raster, ch_meta):
        nodata = ch_meta['nodata']

        # Create output array as float32
        ch_index_raster = np.full_like(ch_raster, fill_value=nodata, dtype="float32")

        # Initialize valid cells to 0.0
        ch_index_raster[(ch_raster == 0)] = 0.
        # Potential CH (1) → 0.5
        ch_index_raster[(ch_raster == 1)] = 0.5
        # Likely CH (10) → 1.0
        ch_index_raster[(ch_raster == 10)] = 1.

        return ch_index_raster


    def load_ch_raster_and_meta(self):
        with rasterio.open(self.ch_raster_path) as ch_src:
            polygon_gdf = load_poligon_gdf(self.wkt_polygon).to_crs(ch_src.crs)
            bounds = polygon_gdf.total_bounds
            pixel_size_x = abs(ch_src.transform.a)
            pixel_size_y = abs(ch_src.transform.e)
            bbox_margin_x = 10 * pixel_size_x
            bbox_margin_y = 10 * pixel_size_y
            gdf_bbox_emargin = box(
                bounds[0] - bbox_margin_x,
                bounds[1] - bbox_margin_y,
                bounds[2] + bbox_margin_x,
                bounds[3] + bbox_margin_y
            )


            ch_cropped, ch_cropped_transform = mask(
                ch_src,
                # polygon_gdf.geometry,
                [gdf_bbox_emargin],
                crop=True,
                filled=True,
                invert=False,
                nodata=ch_src.nodata
            )

            ch_cropped = ch_cropped[0]

            with rasterio.open(
                f'raster_ch_crop.tif',
                'w',
                driver='GTiff',
                height=ch_cropped.shape[0],
                width=ch_cropped.shape[1],
                count=1,
                nodata=ch_src.nodata,
                dtype=np.float32,
                crs=ch_src.crs,
                transform=ch_cropped_transform,
            ) as dst:
                dst.write(ch_cropped, 1)

            ch_meta = dict(ch_src.profile).copy()
            ch_meta.update({
                'transform': ch_cropped_transform,
                'width': ch_cropped.shape[1],
                'height': ch_cropped.shape[0]
            })
            return ch_cropped, ch_meta

    def run(self):
        print('Running CH model.')
        ch_raster, ch_raster_meta = self.load_ch_raster_and_meta()
        ch_index_raster = self.transform_ch_to_index(ch_raster, ch_raster_meta)
        ch_raster_meta['crs'] = str(ch_raster_meta['crs'])
        valid_mask = ch_index_raster != ch_raster_meta['nodata']
        mean_raster_value = float(np.mean(ch_index_raster[valid_mask]))
        std_raster_value =  float(np.std(ch_index_raster[valid_mask]))
        return {
            "country_code": self.country_code,
            "wkt_polygon": self.wkt_polygon,
            "raster_data": {
                "raster": ch_index_raster.tolist(),
                "meta": ch_raster_meta,
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



    model = CHModel(country_code, wkt_polygon=None, db=db)

    # model._reproject_ch(CH_DATASET_PATH)
    result = model.run()
    result['raster_data']['meta']['crs'] = str(result['raster_data']['meta']['crs'])
    print(json.dumps(result, indent=4))

