import numpy as np



class BioRiskBasic(object):
    """
    Basic risk model using simple average of three components CH, PA, and SI (inverted).
    """
    def __init__(self, cache=True, sri_rounding=4, include_pa=True):
        self.include_pa = include_pa
        self.raster_nodata = -9999
        self.cache = cache
        self.sri_rounding = sri_rounding
        self.explainable_data = None
        self.explainable_data_rule_raster = None

    def pre_process(self, ch_raster, pa_raster, sri_raster):
        self.ch_raster = ch_raster
        self.pa_raster = pa_raster
        self.sri_raster = np.round(sri_raster, decimals=self.sri_rounding)
        # self.valid_mask = (self.sri_raster >= 0) & (self.ch_raster >= 0) & (self.pa_raster >= 0)
        # forcing only non-pa input for now
        pa_mask = (self.pa_raster == 0)
        if self.include_pa:
            pa_mask = (self.pa_raster >= 0)
        self.valid_mask = (self.sri_raster >= 0) & (self.ch_raster >= 0) & (pa_mask)

    def post_processing(self):
        pass

    def get_risk_ling_thresholds(self):
        thresholds = {
            'low': 25,
            'medium': 25,
            'high': 25,
        }
        return thresholds

    def get_xai_humam_text(self):
        # fix this, too confusing...
        # explainable data should just be the ids, not the at this point
        # this method should instead transform this into a humam readable text.
        return "Not Available"

    def get_explainability_info(self):
        expl_info = {
            'xai_raster': self.explainable_data_rule_raster,
            'xai_summary_json': {
                'xai_meta': {},
                'xai_humam_text': self.get_xai_humam_text()
            }
        }
        return expl_info

    def run(self, ch_raster, pa_raster, sri_raster):
        self.failed = []
        # print('Preprocessing..')
        self.pre_process(ch_raster, pa_raster, sri_raster)
        # Create empty risk raster with same shape as input (only using one raster, all should be equal)
        risk_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.float64)

        self.explainable_data_rule_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.int16)

        # risk_raster[self.valid_mask] = (
        #     self.ch_raster[self.valid_mask] +
        #     self.pa_raster[self.valid_mask] +
        #     (1 - self.sri_raster[self.valid_mask])
        # ) / 3

        # Apply the operation on the valid mask
        risk_raster[self.valid_mask] = (
            self.ch_raster[self.valid_mask] +
            (1 - self.sri_raster[self.valid_mask])
        ) / 2
        self.post_processing()
        return risk_raster
