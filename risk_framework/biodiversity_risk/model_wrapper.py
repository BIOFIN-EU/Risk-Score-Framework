import numpy as np
from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_origin
from rasterio.mask import mask
from shapely.geometry import mapping



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
        self.geo_id = geo_id
        self.country_code = country_code
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
        self.db = db
        self.setup_risk_model()

    def setup_risk_model(self):
        from .bio_risk_plus import BioRiskPlusFIS
        # replacces these once we have a proper name and impl for all models
        models_map = {
            'YangEtAl2021': BioRiskPlusFIS,
            'SihamEtAl2026': BioRiskPlusFIS,
            'PontesEtAl2026': BioRiskPlusFIS,
        }
        self.risk_model = models_map[self.risk_model_name]


    def get_raster_and_meta_from_ch_response_object(self):
        # is_future = True
        # if period.lower() == "current":
        #     is_future = False
        reg_index_response = self.ch_retrieval_method(self.country_code, self.wkt_polygon, self.geo_id, self.db)
        meta = reg_index_response.raster_data.meta
        meta_dtype = np.dtype(meta['dtype'])

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=meta_dtype)
        return reg_index_response, raster_array, meta

    def get_raster_and_meta_from_pa_response_object(self):
        reg_index_response = self.pa_retrieval_method(self.country_code, self.wkt_polygon, self.geo_id, self.db)
        meta = reg_index_response.raster_data.meta
        meta_dtype = np.dtype(meta['dtype'])

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=meta_dtype)
        return reg_index_response, raster_array, meta

    def get_raster_and_meta_from_sri_response_object(self, climate_scenario, climate_model, period, future):
        reg_index_response = self.sri_retrieval_method(
            self.sri_species_list, self.country_code, self.wkt_polygon, self.geo_id,
            climate_scenario, climate_model, period,
            self.sri_logic_type, self.sri_correction_method,
            self.db,
            future=future
        )
        meta = reg_index_response.raster_data.meta
        meta_dtype = np.dtype(meta['dtype'])

        raster_array = np.array(reg_index_response.raster_data.raster, dtype=meta_dtype)
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
            dest = np.full((h, w), -1, dtype=reference_raster.dtype)

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
                src_nodata=-1,  # <-- ADD THIS
                dst_transform=ref_transform,
                dst_crs=reference_meta['crs'],
                dst_nodata=-1,  # <-- ADD THIS
                resampling=Resampling.bilinear
            )
            # Replace negative areas with reference raster values
            dest[dest < 0] = reference_raster[dest < 0]
            aligned_rasters.append(dest)

        return aligned_rasters

    def run(self, climate_scenario, climate_model, period):
        print('Running RISK model.')
        # if current prediction
        future = True
        if climate_scenario is None:
            climate_scenario = 'current'
            period = climate_scenario
            future = False

        ch_reg, ch_raster, ch_meta = self.get_raster_and_meta_from_ch_response_object()
        pa_reg, pa_raster, pa_meta = self.get_raster_and_meta_from_ch_response_object()
        sri_reg, sri_raster, sri_meta = self.get_raster_and_meta_from_sri_response_object(
            climate_model, climate_model, period, future)

        rasters_list = [sri_raster, ch_raster, pa_raster]
        meta_list = [sri_meta, ch_meta, pa_meta]
        default_meta = sri_meta
        # not sure we need this... they should be all on the same projection...
        # maybe just do a mask crop using the polygon
        # create a validation_mask and pass it to the internal model as well.
        # (only do operations when its valid vask for all component rasters)
        list_of_species_hsi_aligned = self.align_rasters(rasters_list, meta_list)

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
