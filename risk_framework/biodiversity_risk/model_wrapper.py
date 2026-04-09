import numpy as np
from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_origin
from rasterio.mask import mask
from shapely.geometry import mapping

from risk_framework.species_models.glc_retrieve import GLCModel

from risk_framework.web_api.utils import apply_geometry_mask_to_raster, generate_geo_uuid



class BiofinBiodiversityRiskModelWrapper(object):
    def __init__(
        self,
        geo_id,
        country_code,
        wkt_polygon,
        ch_retrieval_method,
        pa_retrieval_method,
        sri_retrieval_method,
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        crop_to_polygon,
        risk_model,
        db,
    ):
        self.country_code = country_code
        self.geo_id = geo_id
        self.country_only_geo_id = generate_geo_uuid(self.country_code)
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)
        self.ch_retrieval_method = ch_retrieval_method
        self.pa_retrieval_method = pa_retrieval_method
        self.sri_retrieval_method = sri_retrieval_method
        self.sri_logic_type = sri_logic_type
        self.sri_correction_method = sri_correction_method
        self.sri_species_list = sri_species_list
        self.crop_to_polygon = crop_to_polygon
        self.risk_model_name = risk_model
        self.raster_nodata = -9999.0
        self.db = db
        self.setup_risk_model()

    def setup_risk_model(self):
        from risk_framework.biodiversity_risk.bio_risk_fuzzy import BioRiskPlusFIS
        from risk_framework.biodiversity_risk.base_risk_model import BioRiskBasic
        # replacces these once we have a proper name and impl for all models
        models_map = {
            'YangEtAl2021': BioRiskBasic,
            'SihamEtAl2026': BioRiskBasic,
            'PontesEtAl2026': BioRiskPlusFIS,
        }
        self.risk_model = models_map[self.risk_model_name](include_pa=True)


    def get_raster_and_meta_from_ch_response_object(self):
        # is_future = True
        # if period.lower() == "current":
        #     is_future = False
        reg_index_response = self.ch_retrieval_method(self.country_code, self.wkt_polygon, self.country_only_geo_id, self.db)
        meta = reg_index_response.raster_data.meta

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=np.float64)
        return reg_index_response, raster_array, meta

    def get_raster_and_meta_from_pa_response_object(self):
        reg_index_response = self.pa_retrieval_method(self.country_code, self.wkt_polygon, self.country_only_geo_id, self.db)
        meta = reg_index_response.raster_data.meta

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=np.float64)
        return reg_index_response, raster_array, meta

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
                resampling=Resampling.nearest # ensure original categories from CH and PA datasets
            )
            aligned_rasters.append(dest)

        return aligned_rasters

    def separate_risk_raster_based_on_glc_group(self, risk_raster, risk_meta):
        glc_model = GLCModel(self.country_code)
        glc_raster, glc_meta = glc_model.get_reproj_to_reference(risk_meta)
        green_risk_raster_g0 = glc_model.add_mask_to_reference(
            reference_raster=risk_raster, ori_reference_meta=risk_meta,
            glc_raster=glc_raster, glc_meta=glc_meta, glc_mask_value=1)
        urban_risk_raster_g1 = glc_model.add_mask_to_reference(
            reference_raster=risk_raster, ori_reference_meta=risk_meta,
            glc_raster=glc_raster, glc_meta=glc_meta, glc_mask_value=0)
        return green_risk_raster_g0, urban_risk_raster_g1


    def calculate_risk_raster_and_meta(self, climate_scenario, climate_model, period, risk_type):


        future = True
        if climate_scenario is None:
            climate_scenario = 'current'
            period = climate_scenario
            future = False

        print('retrieve CH..')
        ch_reg, ch_raster, ch_meta = self.get_raster_and_meta_from_ch_response_object()
        print('retrieve PA..')
        pa_reg, pa_raster, pa_meta = self.get_raster_and_meta_from_pa_response_object()
        print('retrieve SRI..')
        sri_reg, sri_raster, sri_meta = self.get_raster_and_meta_from_sri_response_object(
            climate_model, climate_model, period, future)

        print('Cropping to polygon..')
        if self.crop_to_polygon:
            polygon_gdf = load_poligon_gdf(self.wkt_polygon)
            ch_raster, ch_meta = apply_geometry_mask_to_raster(polygon_gdf, ch_raster, ch_meta, crop=True, nodata=self.raster_nodata)
            pa_raster, pa_meta = apply_geometry_mask_to_raster(polygon_gdf, pa_raster, pa_meta, crop=True, nodata=self.raster_nodata)
            sri_raster, sri_meta = apply_geometry_mask_to_raster(polygon_gdf, sri_raster, sri_meta, crop=True, nodata=self.raster_nodata)


        rasters_list = [sri_raster, ch_raster, pa_raster]
        meta_list = [sri_meta, ch_meta, pa_meta]
        default_meta = sri_meta
        # not sure we need this... they should be all on the same projection...
        # maybe just do a mask crop using the polygon
        # create a validation_mask and pass it to the internal model as well.
        # (only do operations when its valid vask for all component rasters)
        print('Aligning rasters..')
        sri_raster, ch_raster, pa_raster = self.align_rasters(rasters_list, meta_list)


        if risk_type.upper() == 'NonPA'.upper():
            risk_type_pa_mask = (pa_raster == 1)
        else: #'IsPA'
            risk_type_pa_mask = (pa_raster == 0)

        pa_raster[risk_type_pa_mask] = self.raster_nodata

        print('Running risk model..')
        risk_raster = self.risk_model.run(ch_raster=ch_raster, pa_raster=pa_raster, sri_raster=sri_raster)
        print('Done...')
        return risk_raster, default_meta, ch_reg, pa_reg, sri_reg

    def run(self, climate_scenario, climate_model, period, risk_type):
        base_risk_raster, risk_meta, ch_reg, pa_reg, sri_reg = self.calculate_risk_raster_and_meta(
            climate_scenario, climate_model, period, risk_type)

        green_risk_raster, urban_risk_raster = self.separate_risk_raster_based_on_glc_group(base_risk_raster, risk_meta)

        green_valid_mask = green_risk_raster >= 0
        green_mean_raster_value = float(np.mean(green_risk_raster[green_valid_mask]))
        green_std_raster_value =  float(np.std(green_risk_raster[green_valid_mask]))

        urban_valid_mask = urban_risk_raster >= 0
        urban_mean_raster_value = float(np.mean(urban_risk_raster[urban_valid_mask]))
        urban_std_raster_value =  float(np.std(urban_risk_raster[urban_valid_mask]))

        xai_data = self.risk_model.get_explainability_info()
        risk_ling_thresholds = self.risk_model.get_risk_ling_thresholds()
        return {
            "country_code": self.country_code,
            "wkt_polygon": self.wkt_polygon,
            "climate_scenario": climate_scenario,
            "climate_models": [climate_model],
            "period": period,
            "green_raster_data": {
                "raster": green_risk_raster.tolist(),
                "meta": risk_meta,
                'summary_stats': {
                    'mean_raster_value': green_mean_raster_value,
                    'std_raster_value': green_std_raster_value
                },
            },
            "urban_raster_data": {
                "raster": urban_risk_raster.tolist(),
                "meta": risk_meta,
                'summary_stats': {
                    'mean_raster_value': urban_mean_raster_value,
                    'std_raster_value': urban_std_raster_value
                },
            },
            "sri_species_list": self.sri_species_list,
            'sri_logic_type': self.sri_logic_type,
            'sri_correction_method': self.sri_correction_method,
            'crop_to_polygon': self.crop_to_polygon,
            'risk_model': self.risk_model_name,
            'risk_type': risk_type,
            'meta': {
                'ch_reg_id': ch_reg.id,
                'pa_reg_id': pa_reg.id,
                'sri_reg_id': sri_reg.id,
            },
            'xai_data': xai_data,
            'risk_ling_thresholds': risk_ling_thresholds,
        }



if __name__ == '__main__':

    import json
    import rasterio

    from risk_framework.web_api.models.db_operations import (
        retrieve_or_calculate_sri_future_or_current,
        retrieve_or_calculate_ch,
        retrieve_or_calculate_pa,
    )
    country_code = 'NL'
    db = list(get_db())[0]


    geo_id = generate_geo_uuid(country_code)
    wkt_polygon=None
    ch_retrieval_method = retrieve_or_calculate_ch
    pa_retrieval_method = retrieve_or_calculate_pa
    sri_retrieval_method = retrieve_or_calculate_sri_future_or_current
    sri_logic_type = 'fuzzy'
    sri_correction_method = 'HFI'
    sri_species_list = None
    crop_to_polygon = True
    risk_model = 'PontesEtAl2026'
    risk_model = BiofinBiodiversityRiskModelWrapper(
        geo_id,
        country_code,
        wkt_polygon,
        ch_retrieval_method, pa_retrieval_method, sri_retrieval_method,
        sri_logic_type, sri_correction_method, sri_species_list,
        crop_to_polygon=crop_to_polygon, risk_model=risk_model, db=db
    )
    climate_scenario = 'current'
    climate_model = None
    period = 'current'
    result = risk_model.run(climate_scenario, climate_model, period)
