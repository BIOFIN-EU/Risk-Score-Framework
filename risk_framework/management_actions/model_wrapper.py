import numpy as np
from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_origin
from rasterio.mask import mask
from shapely.geometry import mapping

from risk_framework.species_models.glc_retrieve import GLCModel

from risk_framework.climate_resilience.base_cr_model import BaseCRModel
from risk_framework.management_actions.priority_models import MAPriorityModel
from risk_framework.web_api.utils import apply_geometry_mask_to_raster, generate_geo_uuid



class BiofinMAPriorityModelWrapper(object):
    def __init__(
        self,
        geo_id,
        country_code,
        wkt_polygon,
        risk_retrieval_method, #retrieve_or_calculate_risk_future_or_current
        sri_retrieval_method, #retrieve_or_calculate_sri_future_or_current
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        crop_to_polygon,
        risk_model,
        risk_type,
        db,
    ):
        self.country_code = country_code
        self.geo_id = geo_id
        self.country_only_geo_id = generate_geo_uuid(self.country_code)
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)
        self.risk_retrieval_method = risk_retrieval_method
        self.sri_retrieval_method = sri_retrieval_method
        self.sri_logic_type = sri_logic_type
        self.sri_correction_method = sri_correction_method
        self.sri_species_list = sri_species_list
        self.crop_to_polygon = crop_to_polygon
        self.risk_model = risk_model
        self.risk_type = risk_type
        self.raster_nodata = -9999.0
        self.db = db
        self.setup_risk_model()

    def setup_models(self):
        self.cr_model = BaseCRModel()
        self.ma_model = MAPriorityModel(
            risk_thresholds={
                'low': 0.33,
                'medium': 0.66,
                'high': 1.0,
            },
            resilience_thresholds=self.cr_model.get_ling_thresholds()
        )

    def get_raster_and_meta_from_sri_response_object(self, climate_scenario, climate_model, period, future):
        reg_index_response = self.sri_retrieval_method(
            self.sri_species_list, self.country_code, self.wkt_polygon, self.country_only_geo_id,
            climate_scenario, climate_model, period,
            self.sri_logic_type, self.sri_correction_method,
            self.db,
            future=future
        )
        self.sri_species_list = reg_index_response.species_list
        meta = reg_index_response.raster_data.meta

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=np.float64)
        return reg_index_response, raster_array, meta

    def get_raster_and_meta_from_risk_response_object(self):
        climate_scenario = 'current'
        period = climate_scenario
        climate_model = None
        # sri_override_species_list = self.sri_species_list
        # if sri_override_species_list:
        #     sri_override_species_list = sri_override_species_list.split(',')
        crop_to_polygon = False
        reg_index_response = self.risk_retrieval_method(
            self.country_code,
            self.wkt_polygon,
            self.country_only_geo_id,
            climate_scenario,
            climate_model,
            period,
            self.sri_logic_type,
            self.sri_correction_method,
            self.sri_species_list,
            crop_to_polygon,
            self.risk_model,
            self.risk_type,
            self.db,
            future=False
        )

        meta = reg_index_response.raster_data.meta

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=np.float64)
        return reg_index_response, raster_array, meta

    def align_rasters(self, rasters_list, metas_list):
        """
        Align all rasters to the reference raster shape and bounds
        """
        reference_meta = metas_list[0]
        reference_raster = rasters_list[0]
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
        for raster, meta in zip(rasters_list[1:], metas_list[1:]):
            # Create destination array with reference shape
            dest = np.full((h, w), reference_meta['nodata'], dtype=reference_raster.dtype)

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
                src_nodata=meta['nodata'],
                dst_transform=ref_transform,
                dst_crs=reference_meta['crs'],
                dst_nodata=reference_meta['nodata'],
                resampling=Resampling.bilinear
            )
            aligned_rasters.append(dest)

        return aligned_rasters


    def retrieve_all_sri_raster_and_meta(self, climate_model):
        sri_regs = {}
        sri_rasters = {}
        sri_metas = {}
        print('retrieve SRI current, |-2040 and |-2060 periods..')
        print('retrieve SRI current..')

        climate_scenario = 'current'
        period = climate_scenario
        future = False
        curr_sri_reg, curr_sri_raster, curr_sri_meta = self.get_raster_and_meta_from_sri_response_object(
            climate_scenario, climate_model, period, future)
        sri_regs['current'] = curr_sri_reg
        sri_rasters['current'] = curr_sri_raster
        sri_metas['current'] = curr_sri_meta

        future = True
        for climate_scenario in ["ssp245", "ssp585"]:
            for period in ["2021-2040", "2041-2060"]:
                print(f'retrieve SRI using scenario {climate_scenario}, and perido {period}')
                fut_sri_reg, fut_sri_raster, fut_sri_meta = self.get_raster_and_meta_from_sri_response_object(
                climate_scenario, climate_model, period, future)

                sri_key = f'{climate_scenario}_{period}'
                sri_regs[sri_key] = fut_sri_reg
                sri_rasters[sri_key] = fut_sri_raster
                sri_metas[sri_key] = fut_sri_meta
        aligned_rasters = self.align_rasters(list(sri_rasters.values()), list(sri_metas.values()))
        sri_key_list = list(sri_rasters.keys())
        for a_rasters_i, sri_key in enumerate(sri_key_list):
            sri_rasters[sri_key] = aligned_rasters[a_rasters_i]


    def calculate_resilience_raster_and_meta(self, climate_model):
        sri_regs, sri_rasters, sri_metas = self.retrieve_all_sri_raster_and_meta(climate_model)
        current = sri_rasters['current']
        base_meta = sri_metas['current']
        ssp245_2040 = sri_rasters['ssp245_2021-2040']
        ssp245_2060 = sri_rasters['ssp245_2041-2060']
        ssp585_2040 = sri_rasters['ssp585_2021-2040']
        ssp585_2060 = sri_rasters['ssp585_2041-2060']
        cr_raster = self.cr_model.run(
            current,
            ssp245_2040,
            ssp245_2060,
            ssp585_2040,
            ssp585_2060
        )
        return cr_raster, base_meta

    def calculate_priority_raster_and_meta(self, climate_model):
        cr_raster, cr_meta = self.calculate_resilience_raster_and_meta(climate_model)

        risk_reg, risk_raster, risk_meta = self.get_raster_and_meta_from_risk_response_object()



        print('Cropping to polygon..')
        if self.crop_to_polygon:
            polygon_gdf = load_poligon_gdf(self.wkt_polygon)
            cr_raster, cr_meta = apply_geometry_mask_to_raster(polygon_gdf, cr_raster, cr_meta, crop=True, nodata=self.raster_nodata)
            risk_raster, risk_meta = apply_geometry_mask_to_raster(polygon_gdf, risk_raster, risk_meta, crop=True, nodata=self.raster_nodata)

        rasters_list = [cr_raster, risk_raster]
        metas_list = [cr_meta, risk_meta]
        default_meta = metas_list[0]
        cr_raster, risk_raster = self.align_rasters(rasters_list, metas_list)

        # update some settings to proper formatting and threshodls
        self.sri_species_list = risk_reg.sri_species_list
        self.ma_model.risk_thresholds = risk_reg.risk_ling_thresholds
        print('Running MA priority model..')
        priority_raster = self.ma_model.run(risk_raster, cr_raster)
        print('Done...')
        return priority_raster, default_meta

    def run(self, climate_model):
        priority_raster, priorit_meta = self.calculate_priority_raster_and_meta(climate_model)
        # cats_polygons here
        priority_polygons = {
            # all polygons for each priority management action on the rasters
            # eg:
            # 0: "POLYGON((4.598488763140015 52.39690261469849,4.59894780280675 52.387830068910404,4.609625654246968 52.382524758083576,4.6129675938634565 52.40769458650479,4.598488763140015 52.39690261469849))",
        }
        return {
            "country_code": self.country_code,
            "wkt_polygon": self.wkt_polygon,
            "climate_models": [climate_model],
            "sri_species_list": self.sri_species_list,
            'sri_logic_type': self.sri_logic_type,
            'sri_correction_method': self.sri_correction_method,
            'crop_to_polygon': self.crop_to_polygon,
            'risk_model': self.risk_model,
            'risk_type': self.risk_type,
            'recommendations_polygons': priority_polygons,
            'meta': {
                'recommendations_meta': self.ma_model.get_category_info()
            },
        }



if __name__ == '__main__':

    import json
    import rasterio

    # from risk_framework.web_api.models.db_operations import (
    #     retrieve_or_calculate_sri_future_or_current,
    #     retrieve_or_calculate_ch,
    #     retrieve_or_calculate_pa,
    # )
    # country_code = 'NL'
    # db = list(get_db())[0]


    # geo_id = generate_geo_uuid(country_code)
    # wkt_polygon=None
    # ch_retrieval_method = retrieve_or_calculate_ch
    # pa_retrieval_method = retrieve_or_calculate_pa
    # sri_retrieval_method = retrieve_or_calculate_sri_future_or_current
    # sri_logic_type = 'fuzzy'
    # sri_correction_method = 'HFI'
    # sri_species_list = None
    # crop_to_polygon = True
    # risk_model = 'PontesEtAl2026'
    # risk_model = BiofinBiodiversityRiskModelWrapper(
    #     geo_id,
    #     country_code,
    #     wkt_polygon,
    #     ch_retrieval_method, pa_retrieval_method, sri_retrieval_method,
    #     sri_logic_type, sri_correction_method, sri_species_list,
    #     crop_to_polygon=crop_to_polygon, risk_model=risk_model, db=db
    # )
    # climate_scenario = 'current'
    # climate_model = None
    # period = 'current'
    # result = risk_model.run(climate_scenario, climate_model, period)
