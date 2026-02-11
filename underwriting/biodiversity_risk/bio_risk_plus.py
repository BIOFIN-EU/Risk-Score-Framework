import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


from .skfis_extended import ExplainableControlSystemSimulation


# Define Yager AND operator with p=0.5
def yager_and_operator(*args, p=0.5):
    if len(args) == 0:
        return 0
    sum_pow = np.sum([(1 - a) ** p for a in args])
    result = max(0, 1 - (sum_pow ** (1/p)))
    return result


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
            IF CH is potential AND PA is Unprotected AND SI is Medium THEN RISK is Medium
        Original Edge Cases: <-- probably best to add intermediary medium values for rate MFs
            # if Any two are criteria are "good" but one is bad: then Medium-Low, never low.
            IF CH is Likely AND PA is Unprotected AND SI is Low THEN RISK is Medium-Low
            IF CH is Unknown AND PA is Protected AND SI is Low THEN RISK is Medium


    """
    def __init__(self):
        self.default_score_names = ['low', 'medium-low', 'medium', 'medium-high', 'high']
        self.get_rates_uod = lambda: np.arange(0, 1.01, 0.01)
        self.setup_vars_and_mfs()
        self.setup_rules()
        self.fis = ctrl.ControlSystem(self.rules)
        # self.fis_sim = ctrl.ControlSystemSimulation(self.fis, cache=False)
        self.fis_sim = ExplainableControlSystemSimulation(self.fis, cache=False)

    def setup_vars_and_mfs(self):
        self.ch_var = ctrl.Antecedent(self.get_rates_uod(), 'ch')
        self.ch_var['unknown'] = fuzz.trapmf(self.ch_var.universe, [0, 0, 0.2, 0.6])
        self.ch_var['potential'] = fuzz.trimf(self.ch_var.universe, [0.2, 0.5, 0.8])
        self.ch_var['likely'] = fuzz.trapmf(self.ch_var.universe, [0.4, 0.8, 1., 1.])

        # self.ch_var['unknown'] = fuzz.trimf(self.ch_var.universe, [0, 0, 0.60])
        # self.ch_var['potential'] = fuzz.trimf(self.ch_var.universe, [0.2, 0.5, 0.8])
        # self.ch_var['likely'] = fuzz.trimf(self.ch_var.universe, [0.60, 1., 1.])

        # True/False "singleton"  (will actually behave like it for all intents and purposes: tested)
        self.pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
        self.pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
        self.pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)

        self.si_var = ctrl.Antecedent(self.get_rates_uod(), 'si')
        self.si_var.automf(5, names=self.default_score_names)

        # use auto-tri mf as a base, but replace left/right corners with trapezoidals
        self.risk_var = ctrl.Consequent(self.get_rates_uod(), 'risk')
        self.risk_var.automf(5, names=self.default_score_names)
        self.risk_var['low'] = fuzz.trapmf(self.risk_var.universe, [0, 0, 0.1, 0.25])
        self.risk_var['high'] = fuzz.trapmf(self.risk_var.universe, [0.75, 0.9, 1., 1.])

    def _get_low_risk_rules(self):
        new_rules = []
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['high'],
            self.risk_var['low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium-high'],
            self.risk_var['low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & (self.si_var['medium-high'] | self.si_var['high']),
            self.risk_var['low']
        ))

        return new_rules

    def _get_medium_low_risk_rules(self):
        new_rules = []

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & (self.si_var['medium-high'] | self.si_var['high']),
            self.risk_var['medium-low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['medium-high'],
            self.risk_var['medium-low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium-low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['medium-low']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium-high'],
            self.risk_var['medium-low']
        ))

        # Original Edge Cases: <-- probably best to add intermediary medium values for rate MFs
        #     # if Any two are criteria are "good" but one is bad: then Medium-Low, never low.
        #     IF CH is Likely AND PA is Unprotected AND SI is Low THEN RISK is Medium-Low
        #     IF CH is Unknown AND PA is Protected AND SI is Low THEN RISK is Medium
        low_vars_list = [self.ch_var['unknown'], self.pa_var['unprotected'], self.si_var['high']]
        high_vars_list = [self.ch_var['likely'], self.pa_var['protected'], self.si_var['low']]
        for var_i, high_var in enumerate(high_vars_list):
            low_vars = [v for li, v in enumerate(low_vars_list) if var_i != li]
            new_rules.append(ctrl.Rule(
                low_vars[0] & low_vars[1] & high_var,
                self.risk_var['medium-low']
            ))
        return new_rules

    def _get_medium_risk_rules(self):
        new_rules = []

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['medium']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))
        return new_rules

    def _get_medium_high_risk_rules(self):
        new_rules = []

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['low'],
            self.risk_var['medium-high']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['medium-high']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & (self.si_var['medium-high'] | self.si_var['high']),
            self.risk_var['medium-high']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & (self.si_var['low'] | self.si_var['medium-low']),
            self.risk_var['medium-high']
        ))
        # if CH and SI are bad:
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['low'],
            self.risk_var['medium-high']
        ))
        return new_rules

    def _get_high_risk_rules(self):
        new_rules = []
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['low'],
            self.risk_var['high']
        ))
        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & (self.si_var['medium'] | self.si_var['medium-low']),
            self.risk_var['high']
        ))
        # if PA and SI are bad
        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & (self.si_var['low'] | self.si_var['medium-low']),
            self.risk_var['high']
        ))
        return new_rules

    def setup_rules(self):
        new_rules = []

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['high'],
            self.risk_var['low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium-high'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['unprotected'] & self.si_var['low'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['high'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['medium-high'],
            self.risk_var['medium-low']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['unprotected'] & self.si_var['low'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['high'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium-high'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['medium-low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['unprotected'] & self.si_var['low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['high'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['medium-high'],
            self.risk_var['medium']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['medium'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['medium-low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['unknown'] & self.pa_var['protected'] & self.si_var['low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['high'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['medium-high'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['medium'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['medium-low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['potential'] & self.pa_var['protected'] & self.si_var['low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['high'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['medium-high'],
            self.risk_var['medium-high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['medium'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['medium-low'],
            self.risk_var['high']
        ))

        new_rules.append(ctrl.Rule(
            self.ch_var['likely'] & self.pa_var['protected'] & self.si_var['low'],
            self.risk_var['high']
        ))

        self.rules = new_rules

    def map_ch_fuzzy_label_to_crisp(self, chl_raster):
        # defz_method =  'som' if label == 'likely' else 'centroid'
        # Create mapping dictionary
        label_map = {
            0: fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid'), #unknown
            # 0.5: fuzz.defuzz(self.ch_var.universe, self.ch_var['potential'].mf, 'centroid'), # potential
            0.5: 0.5, # avoid rounding errors, the centroid is 0.5 in any case
            1: fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'som'), #likely
        }

        mapped_raster = np.vectorize(label_map.get)(chl_raster)
        return mapped_raster

    def pre_process(self, chl_raster, pa_raster, sri_raster):
        self.chl_raster = chl_raster
        self.pa_raster = pa_raster
        self.sri_raster = sri_raster
        self.ch_raster = self.map_ch_fuzzy_label_to_crisp(self.chl_raster)

    def run(self, chl_raster, pa_raster, sri_raster):
        self.failed = []
        self.pre_process(chl_raster, pa_raster, sri_raster)
        # Create empty risk raster with same shape as input (only using one raster, all should be equal)
        risk_raster = np.zeros_like(self.ch_raster, dtype=np.float64)

        # Get shape for iteration
        rows, cols = self.ch_raster.shape

        # Iterate through each pixel position
        for i in range(rows):
            for j in range(cols):
                risk_raster[i, j] = self.run_single(
                    ch=self.ch_raster[i, j],
                    pa=self.pa_raster[i, j],
                    si=self.sri_raster[i, j]
                )

        return risk_raster

    def run_single(self, **input_kwargs):
        for key, value in input_kwargs.items():
            self.fis_sim.input[key] = value
        self.fis_sim.compute()
        if 'risk' not in self.fis_sim.output:
            self.failed.append((input_kwargs, ))
            return 0
        return self.fis_sim.output['risk']

# class BioRiskPlusExtendedFIS(object):
#     """
#     Fuzzifying Urbanisation and Climate Change Risks to Biodiversity in Europe with Extended details for HFI in rules
#     Original Biodiversity Risk Components:
#         * CH: Critical Habitat: 0???;0.5;1
#         * PA: Protected Area: 0;1
#         * SI: Threatened Species Reachness:
#             * HFI: Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
#     Proposed Biodiversity Risk Components:
#         * CH: Critical Habitat: (0: Unknown, 1: Potential, 10: Likelly)
#         * PA: Protected Area: 0-1 ??? Possibily make it % of area inside protected area?
#         * (Inverted ^-1) SSI: Species Suitability Index*?:
#             * UCC-SRI: Urbanisation and Climate Change Influenced Species Reachness Index: 0-1
#                 * Species Habitat Suitability affected project urbanisation and climate change models (ssp245, ssp585).
#             * HFI: Current Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
#                 - Alternativelly, represent this with mfs and rules to cover both cases where prestine wilderness is treated one way but also accomodate to non-prestine
#     FIS:
#      - Antecedents: CH, PA, SSI
#      - Consequents: (Biodiversity)Risk
#      - Rules:
#         IF CH is Unknown AND PA is Unprotected AND SI is High THEN RISK is Low
#     """
#     def __init__(self, chl_raster, pa_raster, sri_raster, hfi_raster):
#         self.chl_raster = chl_raster
#         self.ch_raster = None
#         self.pa_raster = pa_raster
#         self.sri_raster = sri_raster
#         self.hfi_raster = hfi_raster
#         self.get_rates_uod = lambda: np.arange(0, 1.1, 0.1)

#     def setup_mfs(self):
#         self.ch_var = ctrl.Antecedent(self.get_rates_uod(), 'ch')
#         self.ch_var['unknown'] = fuzz.trapmf(self.ch_var.universe, [0, 0, 0.4, 0.60])
#         self.ch_var['potential'] = fuzz.trimf(self.ch_var.universe, [0.2, 0.6, 0.8])
#         self.ch_var['likely'] = fuzz.trapmf(self.ch_var.universe, [0.50, 0.8, 1., 1.])

#         # True/False "singleton"  (will actually behave like it for all intents and purposes: tested)
#         self.pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
#         self.pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
#         self.pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


#     def map_ch_fuzzy_label_to_crisp(self):
#         # Create mapping dictionary
#         label_map = {
#             0: fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid'), #unknown
#             # 0.5: fuzz.defuzz(self.ch_var.universe, self.ch_var['potential'].mf, 'centroid'), # potential
#             0.5: 0.5, # avoid rounding errors, the centroid is 0.5 in any case
#             1: fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'centroid'), #likely
#         }

#         mapped_raster = np.vectorize(label_map.get)(self.chl_raster)
#         return mapped_raster

#     def setup(self):
#         self.setup_mfs()
#         self.ch_raster = self.map_ch_fuzzy_label_to_crisp()


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
