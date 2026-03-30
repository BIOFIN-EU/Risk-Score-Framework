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


from risk_framework.conf import HFP_DATASET_PATH

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY
)

from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf, reproject_to_crs



class SRIBaseModel(object):
    def __init__(self, geo_id, hsi_retrieval_method, correction_method, country_code, wkt_polygon, db, species_list=None):
        self.hsi_retrieval_method = hsi_retrieval_method
        self.correction_method = correction_method
        self.country_code = country_code
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)

        self.hfp_dataset_raster_path = HFP_DATASET_PATH
        if species_list is None:
            self.species_list = self.get_species_list()
        else:
            self.species_list = species_list
        self.geo_id = geo_id
        self.db = db
        self.sri_no_data = -9999.0

    def get_species_list(self):
        species_list = INDICATOR_SP_PER_COUNTRY.get(self.country_code, [])
        species_list.sort()
        return species_list

    def get_hsi_and_meta_for_one_species(self, species_name, climate_scenario, climate_model, period):
        is_future = True
        if period.lower() == "current":
            is_future = False

        species_hsi = self.hsi_retrieval_method(
            species_name,
            self.country_code,
            self.wkt_polygon,
            self.geo_id,
            climate_scenario,
            climate_model,
            period,
            self.db,
            future=is_future,
        )
        meta = species_hsi.raster_data.meta
        meta_dtype = np.dtype(meta['dtype'])

        raster_array = np.array(species_hsi.raster_data.raster, dtype=meta_dtype)
        return species_hsi, raster_array, meta

    def species_hsi_aggregation_method(self, list_of_species_hsi):
        raise NotImplementedError()

    def align_rasters(self, species_rasters, species_metas):
        """
        Align all rasters to the reference raster shape and bounds
        """
        reference_meta = species_metas[0]
        reference_raster = species_rasters[0]
        h = reference_meta['height']
        w = reference_meta['width']
        aligned_rasters = []

        # Create reference transform
        ref_transform = from_origin(
            reference_meta['transform'][2],
            reference_meta['transform'][5],
            reference_meta['transform'][0],
            abs(reference_meta['transform'][4])
        )
        aligned_rasters.append(reference_raster)
        for raster, meta in zip(species_rasters[1:], species_metas[1:]):
            # Create destination array with reference shape
            dest = np.full((h, w), self.sri_no_data, dtype=reference_raster.dtype)

            # Create source transform
            src_transform = from_origin(
                meta['transform'][2],
                meta['transform'][5],
                meta['transform'][0],
                abs(meta['transform'][4])
            )

            # Simple reprojection
            reproject(
                source=raster,
                destination=dest,
                src_transform=src_transform,
                src_crs=meta['crs'],
                src_nodata=self.sri_no_data,  # <-- ADD THIS
                dst_transform=ref_transform,
                dst_crs=reference_meta['crs'],
                dst_nodata=self.sri_no_data,  # <-- ADD THIS
                resampling=Resampling.bilinear
            )
            # Replace negative areas with reference raster values
            dest[dest < 0] = reference_raster[dest < 0]
            aligned_rasters.append(dest)

        return aligned_rasters

    def inverted_hfi_normalization(self, hfi_raster):
        valid_raster = hfi_raster >= 0
        norm_hfi_raster = hfi_raster.copy()
        norm_hfi_raster.astype(np.float32)

        norm_hfi_raster[valid_raster] = (100 - (2 * hfi_raster[valid_raster])) / (100 + (21 * hfi_raster[valid_raster]))
        # norm_hfi_raster[valid_raster] = (23 * hfi_raster[valid_raster]) / (100 + (21 * hfi_raster[valid_raster]))

        return norm_hfi_raster

    def load_hfp_raster_and_transform(self):
        # Open HF raster
        with rasterio.open(self.hfp_dataset_raster_path) as hfp_src:
            polygon_gdf = load_poligon_gdf(self.wkt_polygon).to_crs(hfp_src.crs)
            bounds = polygon_gdf.total_bounds
            pixel_size_x = abs(hfp_src.transform.a)
            pixel_size_y = abs(hfp_src.transform.e)
            bbox_margin_x = 10 * pixel_size_x
            bbox_margin_y = 10 * pixel_size_y
            gdf_bbox_emargin = box(
                bounds[0] - bbox_margin_x,
                bounds[1] - bbox_margin_y,
                bounds[2] + bbox_margin_x,
                bounds[3] + bbox_margin_y
            )


            hfp_cropped, hfp_cropped_transform = mask(
                hfp_src,
                [gdf_bbox_emargin],
                crop=True,
                filled=True,
                invert=False,
                nodata=-9999
                # all_touched=True
            )

            hfp_cropped = hfp_cropped[0]

            # with rasterio.open(
            #     f'raster_hfi_hfp_cropped.tif',
            #     'w',
            #     driver='GTiff',
            #     height=hfp_cropped.shape[0],
            #     width=hfp_cropped.shape[1],
            #     count=1,
            #     dtype=np.float32,
            #     crs=hfp_src.crs,
            #     # transform=clipped_hfp_transform['transform'],  # rasterio accepts the affine directly
            #     transform=hfp_cropped_transform,  # rasterio accepts the affine directly
            # ) as dst:
            #     dst.write(hfp_cropped, 1)

            hfp_meta = dict(hfp_src.profile).copy()
            hfp_meta.update({
                'transform': hfp_cropped_transform,
                'width': hfp_cropped.shape[1],
                'height': hfp_cropped.shape[0]
            })
            norm_hfi_raster = self.inverted_hfi_normalization(hfp_cropped)
            return norm_hfi_raster, hfp_cropped_transform

    def apply_correction_method(self, sri_raster, sri_raster_meta):
        if self.correction_method is None:
            return sri_raster
        else:
            norm_hfi_raster, clipped_hfp_transform = self.load_hfp_raster_and_transform()
            hfi_resampled = np.empty(sri_raster.shape, dtype=np.float32)
            reproject(
                source=norm_hfi_raster,
                destination=hfi_resampled,
                src_transform=clipped_hfp_transform,
                src_crs=sri_raster_meta['crs'],
                dst_transform=sri_raster_meta['transform'],
                dst_crs=sri_raster_meta['crs'],
                resampling=Resampling.bilinear
            )

            # with rasterio.open(
            #     f'raster_hfi_clipped_rep.tif',
            #     'w',
            #     driver='GTiff',
            #     height=norm_hfi_raster.shape[0],
            #     width=norm_hfi_raster.shape[1],
            #     count=1,
            #     dtype=np.float32,
            #     crs=sri_raster_meta['crs'],
            #     # transform=clipped_hfp_transform['transform'],  # rasterio accepts the affine directly
            #     transform=clipped_hfp_transform,  # rasterio accepts the affine directly
            # ) as dst:
            #     dst.write(norm_hfi_raster, 1)

            # Create mask where SRI and HFI has valid data (not >= 0)
            valid_mask = (sri_raster >= 0) & (hfi_resampled >= 0)

            # Only multiply where mask is True
            sri_raster[valid_mask] *= hfi_resampled[valid_mask]
            return sri_raster

    def run(self, climate_scenario, climate_model, period):
        print('Running SRI model.')
        # if current prediction
        if climate_scenario is None:
            climate_scenario = 'current'
            period = climate_scenario

        hsi_registry_list = []
        list_of_species_hsi = []
        list_of_species_meta = []
        for species_name in self.species_list:
            species_hsi_reg, species_hsi_raster, meta = self.get_hsi_and_meta_for_one_species(species_name, climate_scenario, climate_model, period)
            hsi_registry_list.append(species_hsi_reg.id)
            list_of_species_hsi.append(species_hsi_raster)
            list_of_species_meta.append(meta)

        default_meta = list_of_species_meta[0]
        list_of_species_hsi_aligned = self.align_rasters(list_of_species_hsi, list_of_species_meta)

        non_corrected_sri_raster = self.species_hsi_aggregation_method(list_of_species_hsi_aligned)

        sri_raster = self.apply_correction_method(non_corrected_sri_raster, default_meta)

        valid_mask = sri_raster >= 0
        mean_raster_value = float(np.mean(sri_raster[valid_mask]))
        std_raster_value =  float(np.std(sri_raster[valid_mask]))

        return {
            "species_list": self.species_list,
            "country_code": self.country_code,
            "wkt_polygon": self.wkt_polygon,
            "climate_scenario": climate_scenario,
            "climate_models": [climate_model],
            "period": period,
            "raster_data": {
                "raster": sri_raster.tolist(),
                "meta": default_meta,
                'summary_stats': {
                    'mean_raster_value': mean_raster_value,
                    'std_raster_value': std_raster_value
                },
            },
            'logic_type': None,
            'correction_method': self.correction_method,
            'meta': {
                'hsi_id_list': hsi_registry_list
                # 'hsi_registry_list': hsi_registry_list
            }
        }



class FuzzySRIModel(SRIBaseModel):
    def species_hsi_aggregation_method(self, list_of_species_hsi):
        stacked = np.stack(list_of_species_hsi)
        # Calculate fuzzy mean (mean across species axis)
        fuzzy_mean = np.mean(stacked, axis=0)

        return fuzzy_mean

    def run(self, climate_scenario, climate_model, period):
        data = super().run(climate_scenario, climate_model, period)
        data['logic_type'] = 'fuzzy'
        return data


if __name__ == '__main__':
    import json
    import rasterio

    from risk_framework.web_api.utils import get_db
    country_code = 'NL'
    db = list(get_db())[0]
    fsri = FuzzySRIModel(country_code, wkt_polygon=None, db=db)

    result = fsri.run(climate_scenario='ssp245', climate_model='EC-Earth3-Veg', period='2021-2040')


    meta = result['raster_data']['meta']
    dtype = meta['dtype']
    # predictor = meta['predictor']
    compress = meta['compress']
    raster_value = result['raster_data']['raster']
    # raster_value = out_image[0]  # Remove the band dimension
    raster = np.array(raster_value, dtype=np.dtype(dtype))
    # Create transform object for rasterio
    # transform = from_origin(
    #     meta['transform'][2],  # top-left x
    #     meta['transform'][5],  # top-left y
    #     meta['transform'][0],  # pixel width
    #     # abs(meta['transform'][4])  # pixel height (make positive)
    #     abs(meta['transform'][4])  # pixel height (make positive)
    # )
    # # Save as GeoTIFF - rasterio handles the transform directly
    with rasterio.open(
        'probability_raster_fsriall.tif',
        'w',
        driver='GTiff',
        height=raster.shape[0],
        width=raster.shape[1],
        count=1,
        dtype=raster.dtype,
        crs=meta['crs'],
        transform=meta['transform'],  # rasterio accepts the affine directly
        nodata=-1
    ) as dst:
        dst.write(raster, 1)
    print(json.dumps(result, indent=4))
