
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

    def run(self, climate_scenario, climate_model, period):
        pass
