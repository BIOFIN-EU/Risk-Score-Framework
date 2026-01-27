import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class BioRiskPlusFIS(object):
    """
    Fuzzifying Urbanisation and Climate Change Risks to Biodiversity in Europe
    Original Biodiversity Risk Components:
        * CH: Critical Habitat: 0???;0.5;1
        * PA: Protected Area: 0;1
        * SI: Threatened Species Reachness:
    Proposed Biodiversity Risk Components:
        * CH: Critical Habitat: (0: Unknown, 1: Potential, 10: Likelly)
        * PA: Protected Area: 0-1 ??? Possibily make it % of area inside protected area?
        * (Inverted ^-1) UCC-SRI: Urbanisation and Climate Change Influenced Species Reachness Index: 0-1
    FIS:
     - Antecedents: CH, PA, SRI (this is the one with HFI already applied to it)
     - Consequents: (Biodiversity)Risk
     - Rules:
        Extreme cases:
            IF CH is Likely AND PA is Protected AND SI is Low THEN RISK is High
            IF CH is Unknown AND PA is Unprotected AND SI is High THEN RISK is Low
        Medium:
            IF CH is Possibly AND PA is Unprotected AND SI is Medium THEN RISK is Medium <-- probably best to add intermediary values
        Original Edge Cases:
            IF CH is Likely AND PA is Unprotected AND SI is Low THEN RISK is Medium
            IF CH is Unknown AND PA is Protected AND SI is Low THEN RISK is Medium


    """
    def __init__(self, chl_raster, pa_raster, sri_raster):
        self.chl_raster = chl_raster
        self.ch_raster = None
        self.pa_raster = pa_raster
        self.sri_raster = sri_raster
        self.get_rates_uod = lambda: np.arange(0, 1.1, 0.1)

    def setup_mfs(self):
        self.ch_var = ctrl.Antecedent(self.get_rates_uod(), 'ch')
        self.ch_var['unknown'] = fuzz.trapmf(self.ch_var.universe, [0, 0, 0.4, 0.60])
        self.ch_var['potential'] = fuzz.trimf(self.ch_var.universe, [0.2, 0.6, 0.8])
        self.ch_var['likely'] = fuzz.trapmf(self.ch_var.universe, [0.50, 0.8, 1., 1.])

        # True/False "singleton"  (will actually behave like it for all intents and purposes: tested)
        self.pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
        self.pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
        self.pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


    def map_ch_fuzzy_label_to_crisp(self):
        # Create mapping dictionary
        label_map = {
            0: fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid'), #unknown
            0.5: fuzz.defuzz(self.ch_var.universe, self.ch_var['potential'].mf, 'centroid'), # potential
            1: fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'centroid'), #likely
        }

        mapped_raster = np.vectorize(label_map.get)(self.chl_raster)
        return mapped_raster

    def setup(self):
        self.setup_mfs()
        self.ch_raster = self.map_ch_fuzzy_label_to_crisp()



class BioRiskPlusExtendedFIS(object):
    """
    Fuzzifying Urbanisation and Climate Change Risks to Biodiversity in Europe with Extended details for HFI in rules
    Original Biodiversity Risk Components:
        * CH: Critical Habitat: 0???;0.5;1
        * PA: Protected Area: 0;1
        * SI: Threatened Species Reachness:
            * HFI: Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
    Proposed Biodiversity Risk Components:
        * CH: Critical Habitat: (0: Unknown, 1: Potential, 10: Likelly)
        * PA: Protected Area: 0-1 ??? Possibily make it % of area inside protected area?
        * (Inverted ^-1) SSI: Species Suitability Index*?:
            * UCC-SRI: Urbanisation and Climate Change Influenced Species Reachness Index: 0-1
                * Species Habitat Suitability affected project urbanisation and climate change models (ssp245, ssp585).
            * HFI: Current Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
                - Alternativelly, represent this with mfs and rules to cover both cases where prestine wilderness is treated one way but also accomodate to non-prestine
    FIS:
     - Antecedents: CH, PA, SSI
     - Consequents: (Biodiversity)Risk
     - Rules:
        IF CH is Unknown AND PA is Unprotected AND SI is High THEN RISK is Low
    """
    def __init__(self, chl_raster, pa_raster, sri_raster, hfi_raster):
        self.chl_raster = chl_raster
        self.ch_raster = None
        self.pa_raster = pa_raster
        self.sri_raster = sri_raster
        self.hfi_raster = hfi_raster
        self.get_rates_uod = lambda: np.arange(0, 1.1, 0.1)

    def setup_mfs(self):
        self.ch_var = ctrl.Antecedent(self.get_rates_uod(), 'ch')
        self.ch_var['unknown'] = fuzz.trapmf(self.ch_var.universe, [0, 0, 0.4, 0.60])
        self.ch_var['potential'] = fuzz.trimf(self.ch_var.universe, [0.2, 0.6, 0.8])
        self.ch_var['likely'] = fuzz.trapmf(self.ch_var.universe, [0.50, 0.8, 1., 1.])

        # True/False "singleton"  (will actually behave like it for all intents and purposes: tested)
        self.pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
        self.pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
        self.pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


    def map_ch_fuzzy_label_to_crisp(self):
        # Create mapping dictionary
        label_map = {
            0: fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid'), #unknown
            0.5: fuzz.defuzz(self.ch_var.universe, self.ch_var['potential'].mf, 'centroid'), # potential
            1: fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'centroid'), #likely
        }

        mapped_raster = np.vectorize(label_map.get)(self.chl_raster)
        return mapped_raster

    def setup(self):
        self.setup_mfs()
        self.ch_raster = self.map_ch_fuzzy_label_to_crisp()


# if __name__ == '__main__':
#     chl_raster = np.array([
#         [0, 1,  0.5,   0],
#         [0.5, 0,  1, 0.5],
#         [1, 0.5,  0,   1]
#     ], dtype=np.float32)
#     pa_raster = np.array([
#         [0, 1,  0, 0],
#         [0, 0,  1, 0],
#         [1, 0,  0, 1]
#     ], dtype=np.float32)

#     sri_raster = np.array([
#         [0.1,   1,  0.5,   0],
#         [0.5,   0,    1, 0.5],
#         [1,   0.5,    0, 0.1]
#     ], dtype=np.float32)
#     hfi_raster = np.array([
#         [0,   4,  0,   10],
#         [4,   0,    7, 30],
#         [20,   40,    0, 50]
#     ], dtype=np.int16)


#     fis = BioRiskPlusFIS(chl_raster, pa_raster, sri_raster, hfi_raster)
#     fis.setup()
#     expected_ch_raster = np.array([
#         [0.25, 0.81,  0.53,   0.25],
#         [0.53, 0.25,  0.81, 0.53],
#         [0.81, 0.53,  0.25,   0.81]
#     ], dtype=np.float32)
#     np.testing.assert_array_almost_equal(fis.ch_raster,expected_ch_raster, decimal=2)
