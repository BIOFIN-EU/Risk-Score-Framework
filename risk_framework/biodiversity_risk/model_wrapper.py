import numpy as np
from risk_framework.web_api.utils import get_country_wkt, load_poligon_gdf



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

    def get_raster_and_meta_from_sri_response_object(self, climate_scenario, climate_model, period):
        # (override_species_list, country_code, wkt_polygon, geo_id,
        # climate_scenario, climate_model, period, logic_type, correction_method, db, future=False):
        future = False # fix this
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

    def run(self, climate_scenario, climate_model, period):
        print('Running RISK model.')
        # if current prediction
        if climate_scenario is None:
            climate_scenario = 'current'
            period = climate_scenario

        species_sri_reg, species_hsi_raster, meta =

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
