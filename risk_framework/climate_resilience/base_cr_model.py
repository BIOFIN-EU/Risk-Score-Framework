import numpy as np

import numpy as np


class BaseCRModel(object):
    """
    Basic climate resilience model based on Noah et al. (2021), in which
    sites with suitable habitat across all scenarios are climatically resilient.

    Following Noah et al. (2021), who required habitat suitability of a single species
    across both multiple time horizons and multiple climate scenarios, we extend their
    logic to a multi-species context using the Species Richness Index that aggregate
    the habitat suitability of the indicator species in the region species.

    Our continuous resilience score (0-1) is calculated as:
        1. Calculate the average Species Richness Index for each climate scenario (SSP245 and SSP585)
          across two future periods (2020-2040, and 2041-2060):
           avg_ssp245 = mean(R_2040, R_2060) under SSP245
           avg_ssp585 = mean(R_2040, R_2060) under SSP585

        2. Calculate scenario-specific persistence base on the current conditions:
           change245 = avg_ssp245 - R_current
           change585 = avg_ssp585 - R_current

        3. Normalize from [-1, 1] to resilience score [0, 1]

        4. Final resilience score = min(r245, r585)

    The min() operation implements Noah's "suitable across all scenarios" logic, where a site's
    resilience is limited by its weakest scenario performance for a conservative view.
    Three equally spaced thresholds classify
    resilience categories: low (<=0.33), medium (0.34-0.66), high (>=0.67),
    instead of Noah's binary classification using the 0.5 threshold.
    """
    def __init__(self):
        self.raster_nodata = -9999

    def pre_process(self, current, ssp245_2040, ssp245_2060, ssp585_2040, ssp585_2060):
        self.current = current
        self.ssp245_2040 = ssp245_2040
        self.ssp245_2060 = ssp245_2060
        self.ssp585_2040 = ssp585_2040
        self.ssp585_2060 = ssp585_2060
        self.valid_mask = (
            (self.current >= 0) & \
            (self.ssp245_2040 >= 0) & (self.ssp245_2060 >= 0) & \
            (self.ssp585_2040 >= 0) & (self.ssp585_2060 >= 0)
        )

    def post_processing(self):
        pass

    def get_ling_thresholds(self):
        thresholds = {
            'low': 0.33,
            'medium': 0.66,
            'high': 1.0,
        }
        return thresholds

    def get_explainability_info(self):
        expl_info = {
        }
        return expl_info

    def normalize(self, change):
        return (change + 1.0) / 2.0

    def run(self, current, ssp245_2040, ssp245_2060, ssp585_2040, ssp585_2060):
        self.failed = []
        # print('Preprocessing..')
        self.pre_process(current, ssp245_2040, ssp245_2060, ssp585_2040, ssp585_2060)
        # Create empty raster with same shape as input (only using one raster, all should be equal sizes)
        resilience_raster = np.full_like(self.current, self.raster_nodata, dtype=np.float64)

        # Calculate average proportional persistence for each scenario
        avg_ssp245 = (self.ssp245_2040[self.valid_mask] + self.ssp245_2060[self.valid_mask]) / 2.0
        avg_ssp585 = (self.ssp585_2040[self.valid_mask] + self.ssp585_2060[self.valid_mask]) / 2.0

        change245 = avg_ssp245 - self.current[self.valid_mask]
        change585 = avg_ssp585 - self.current[self.valid_mask]

        r245 = self.normalize(change245)
        r585 = self.normalize(change585)

        # Final resilience: weakest scenario performance
        resilience_raster[self.valid_mask] = np.minimum(r245, r585)


        self.post_processing()
        return resilience_raster
