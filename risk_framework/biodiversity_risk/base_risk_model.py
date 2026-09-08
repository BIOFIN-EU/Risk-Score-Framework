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
            'low': 0.33,
            'medium': 0.66,
            'high': 1.0,
        }
        return thresholds

    @classmethod
    def get_category_info(cls):
        """Return metadata about each priority category."""
        return {
            0: {
                "label": "low",
                "label_short": "low",
                "description": "Low risk of loosing biodiversity.",
                "color": "#2EF302",
            },
            1: {
                "label": "medium",
                "label_short": "medium",
                "description": "Medium risk of loosing biodiversity.",
                "color": "#ff9500",
            },
            2: {
                "label": "high",
                "label_short": "high",
                "description": "High risk of loosing biodiversity.",
                "color": "#ff0000"
            }
        }

    def get_xai_humam_text(self):

        # base_template = 'This region {pa_text} with {critical_text} exhibits a {sri_text}. These characteristics collectively indicate a {risk_text}.'

        base_template = "This region {{protected_area}} with {{critical_habitat}} status and exhibits a {{species_richness}}. These characteristics collectively indicate a {{biodiversity_loss}} in the overall region."

        pa_text = "is within a Protected Area" if self.has_pa else "is not within a Protected Area"

        risk_xai = {
            "template": base_template,
            "placeholders": {
                "protected_area": {
                    "text": pa_text,
                    "data_type": "protected_area_assessment"
                },
                "critical_habitat": {
                    "text": f"{self.avg_ch_score_text} Critical Habitat",
                    "data_type": "critical_habitat_status"
                },
                "species_richness": {
                    "text": "low Species Richness Index",
                    "data_type": "species_richness_metrics"
                },
                "biodiversity_loss": {
                    "text": f"{self.avg_risk_score_text} vulnerability and likelihood of Biodiversity Loss",
                    "data_type": "biodiversity_loss_assessment"
                }
            }
        }
        return risk_xai

    def get_explainability_info(self):
        expl_info = {
            'xai_raster': self.explainable_data_rule_raster,
            'xai_summary_json': {
                'xai_meta': {},
                'xai_humam_text': self.get_xai_humam_text()
            }
        }
        return expl_info

    def _class_from_value_and_thresholds(self, value):
        class_text = None
        for k, v in self.get_risk_ling_thresholds().items():
            if value < v:
                class_text = k
                break
        return class_text

    def run(self, ch_raster, pa_raster, sri_raster):
        self.failed = []
        # print('Preprocessing..')
        self.pre_process(ch_raster, pa_raster, sri_raster)
        # Create empty risk raster with same shape as input (only using one raster, all should be equal)
        risk_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.float64)

        self.explainable_data_rule_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.int16)

        self.has_pa = np.any(self.pa_raster[self.valid_mask] == 1)

        self.avg_ch_score = np.mean(self.ch_raster[self.valid_mask])
        self.avg_risk_score = np.mean(risk_raster[self.valid_mask])
        self.avg_risk_score_text = self._class_from_value_and_thresholds(self.avg_risk_score)

        if self.avg_ch_score > 0.65:
            self.avg_ch_score_text = 'Likely'
        elif self.avg_ch_score > 0.25:
            self.avg_ch_score_text = 'Potential'
        else:
            self.avg_ch_score_text = 'Unknown'

        # Apply the operation on the valid mask
        if self.include_pa:
            risk_raster[self.valid_mask] = (
                self.ch_raster[self.valid_mask] +
                self.pa_raster[self.valid_mask] +
                (1 - self.sri_raster[self.valid_mask])
            ) / 3

        else:
            risk_raster[self.valid_mask] = (
                self.ch_raster[self.valid_mask] +
                (1 - self.sri_raster[self.valid_mask])
            ) / 2
        self.post_processing()
        return risk_raster
