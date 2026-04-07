from functools import lru_cache
from collections import Counter
import pickle

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


from risk_framework.biodiversity_risk.skfis_extended import ExplainableControlSystemSimulation
from risk_framework.conf import RISK_FUZZY_CACHED_FILE


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
    def __init__(self, cache=True, sri_rounding=4, include_pa=True):
        self.include_pa = include_pa
        self.raster_nodata = -9999
        self.default_score_names = ['low', 'medium-low', 'medium', 'medium-high', 'high']
        self.get_rates_uod = lambda: np.arange(0, 1.01, 0.01)
        self.setup_vars_and_mfs()
        self.setup_rules()
        self.cache = cache
        self.sri_rounding = sri_rounding
        self.fis = ctrl.ControlSystem(self.rules)
        # self.fis_sim = ctrl.ControlSystemSimulation(self.fis, cache=False)
        self.fis_sim = ExplainableControlSystemSimulation(self.fis, cache=cache)
        self.fis_sim.si_rounding = self.sri_rounding
        self.explainable_data = None
        self.explainable_data_rule_raster = None
        self.loaded_cache_db = None
        self.setup_cache_db()

    def prepare_risk_cache_db(self):
        """Precompute all possible combinations and save to cache file"""

        # Define all possible values
        ch_values = [
            np.float64(self.map_ch_fuzzy_label_to_crisp(0.0)),
            np.float64(self.map_ch_fuzzy_label_to_crisp(0.5)),
            np.float64(self.map_ch_fuzzy_label_to_crisp(1.0))
        ]
        pa_values = [0.0, 1.0]

        # Generate si values from 0 to 1 inclusive with step 0.0001
        si_values = np.arange(0.0, 1.0001, 0.0001).round(4).tolist()

        # Create cache dictionary
        cache_db = {}

        # Calculate total combinations for progress tracking
        total_combinations = len(ch_values) * len(pa_values) * len(si_values)
        processed = 0

        print(f"Preparing risk cache database...")
        print(f"  ch values: {ch_values}")
        print(f"  pa values: {pa_values}")
        print(f"  si values: {len(si_values)} (0.0000 to 1.0000)")
        print(f"  Total combinations: {total_combinations:,}")
        print()

        # Iterate through all combinations
        for ch in ch_values:
            for pa in pa_values:
                for si in si_values:
                    # Create cache key
                    cache_key = self.get_cache_id_for_input(ch, pa, si)

                    # Run the model
                    output, explainable_data = self.run_single_preprocessed(
                        ch=ch,
                        pa=pa,
                        si=si
                    )

                    # Convert numpy types to Python native types for JSON serialization
                    if isinstance(output, np.floating):
                        output = float(output)

                    # Store in cache database
                    cache_db[cache_key] = {
                        'output': output,
                        'explainable_data': explainable_data
                    }

                    # Update progress
                    processed += 1
                    if processed % 1000 == 0 or processed == total_combinations:
                        percent = (processed / total_combinations) * 100
                        print(f"Progress: {processed:,}/{total_combinations:,} ({percent:.1f}%)")

        # Save to Pickled bin file
        print(f"\nSaving cache to {RISK_FUZZY_CACHED_FILE}...")
        try:
            with open(RISK_FUZZY_CACHED_FILE, 'wr') as f:
                pickle.dump(cache_db, f)
            print(f"Successfully saved {len(cache_db):,} entries to cache file")
        except Exception as e:
            print(f"Error saving cache: {e}")

        return cache_db

    def get_cache_id_for_input(self, ch, pa, si):
        si_rounded = np.round(si, decimals=self.sri_rounding)
        ch_rounded = np.round(ch, decimals=self.sri_rounding)
        # Create cache key
        cache_key = f"{ch_rounded:.4f}_{pa}_{si_rounded:.4f}"
        return cache_key

    def setup_cache_db(self):
        if self.cache:
            with open(RISK_FUZZY_CACHED_FILE, 'rb') as f:
                self.loaded_cache_db = pickle.load(f)


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
        self.risk_var['high'] = fuzz.trapmf(self.risk_var.universe, [0.85, 0.95, 1., 1.])
        # self.risk_var['high'] = fuzz.trapmf(self.risk_var.universe, [0.75, 0.9, 1., 1.])

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
            self.risk_var['medium-low']
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
            self.risk_var['medium-high']
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
        # label_map = {
        #     np.float64(0): fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid'), #unknown
        #     # 0.5: fuzz.defuzz(self.ch_var.universe, self.ch_var['potential'].mf, 'centroid'), # potential
        #     np.float64(0.5): np.float64(0.5), # avoid rounding errors, the centroid is 0.5 in any case
        #     np.float64(1): fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'lom'), #likely
        #     self.raster_nodata: self.raster_nodata
        # }

        # mapped_raster = np.vectorize(label_map.get)(chl_raster)

        mapped_raster = np.full_like(chl_raster, self.raster_nodata)
        # Get defuzzified values
        unknown_val = fuzz.defuzz(self.ch_var.universe, self.ch_var['unknown'].mf, 'centroid')
        likely_val = fuzz.defuzz(self.ch_var.universe, self.ch_var['likely'].mf, 'lom')
        # Apply threshold-based mapping ,
        # putting here intervals to stop flot point messing up the mappign
        # mapping 0:
        mask_unknown = (chl_raster >= 0) & (chl_raster < 0.3)
        mapped_raster[mask_unknown] = unknown_val

        # mapping 0.5:
        mask_potential = (chl_raster >= 0.3) & (chl_raster <= 0.7)
        mapped_raster[mask_potential] = 0.5

        # mapping 1.0:
        mask_likely = (chl_raster > 0.7) & (chl_raster <= 1)
        mapped_raster[mask_likely] = likely_val

        return mapped_raster

    def pre_process(self, ch_raster, pa_raster, sri_raster):
        # ch with linguistic based values. not the final index values
        self.chl_raster = ch_raster
        self.pa_raster = pa_raster
        self.sri_raster = np.round(sri_raster, decimals=self.sri_rounding)
        self.ch_raster = self.map_ch_fuzzy_label_to_crisp(self.chl_raster)
        pa_mask = (self.pa_raster == 0)
        if self.include_pa:
            pa_mask = (self.pa_raster >= 0)
        self.valid_mask = (self.sri_raster >= 0) & (self.ch_raster >= 0) & (pa_mask)

    def post_processing(self):
        valid_rules = self.explainable_data_rule_raster[
            self.explainable_data_rule_raster != -1
        ].flatten().tolist()
        rule_counter = Counter(valid_rules)

        # Get top 5
        top_5_rules_activated = rule_counter.most_common(5)
        self.explainable_data = self.fis_sim.get_rules_string_by_id_list(top_5_rules_activated)

    def get_risk_ling_thresholds(self):
        centroid_thresholds = {}
        for term_label, term  in self.risk_var.terms.items():
            centroid_thresholds[term_label] = float(fuzz.defuzz(self.risk_var.universe, term.mf, 'centroid'))
        return centroid_thresholds

    def get_xai_humam_text(self):
        # fix this, too confusing...
        # explainable data should just be the ids, not the at this point
        # this method should instead transform this into a humam readable text.
        return self.explainable_data

    def get_explainability_info(self):
        expl_info = {
            'xai_raster': self.explainable_data_rule_raster,
            'xai_summary_json': {
                'xai_meta': self.fis_sim.get_all_rules_id_components_map(),
                'xai_humam_text': self.get_xai_humam_text()
            }
        }
        return expl_info

    def run(self, ch_raster, pa_raster, sri_raster):
        self.failed = []
        print('Preprocessing..')
        self.pre_process(ch_raster, pa_raster, sri_raster)
        # Create empty risk raster with same shape as input (only using one raster, all should be equal)
        risk_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.float64)

        self.explainable_data_rule_raster = np.full_like(self.ch_raster, self.raster_nodata, dtype=np.int16)
        # Get shape for iteration
        rows, cols = self.ch_raster.shape

        # total_pixels = rows * cols
        # valid_pixels = np.sum(self.valid_mask)
        # processed_pixels = 0
        # last_percent = 0
        # print(f"Total pixels: {total_pixels:,}")
        # print(f"Valid pixels: {valid_pixels:,} ({valid_pixels/total_pixels*100:.1f}%)")
        # print("Processing...")

        print('Running each pixel..')
        # Iterate through each pixel position
        for i in range(rows):
            for j in range(cols):
                if self.valid_mask[i, j]:
                    pixel_result, last_explainable_data = self.run_single_preprocessed(
                        ch=self.ch_raster[i, j],
                        pa=self.pa_raster[i, j],
                        si=self.sri_raster[i, j]
                    )
                    risk_raster[i, j] = pixel_result
                    if last_explainable_data:
                        # retrieve only top activated rule id that
                        top_activated_rule_data = list(last_explainable_data['activated_rules'].values())[0]
                        rule_id = top_activated_rule_data['rule_id']
                        self.explainable_data_rule_raster[i, j] = rule_id

                    # processed_pixels += 1
                    # # Print progress every 1%
                    # current_percent = int(processed_pixels / valid_pixels * 100)
                    # if current_percent > last_percent:
                    #     last_percent = current_percent
                    #     print(f"Progress: {current_percent}% ({processed_pixels:,}/{valid_pixels:,} pixels)")

        # print(f"Processing complete: {processed_pixels:,}/{valid_pixels:,} pixels (100%)")
        self.post_processing()
        return risk_raster

    # def run_single(self, **input_kwargs):
    #     for key, value in input_kwargs.items():
    #         value = np.float64(value)
    #         self.fis_sim.input[key] = value
    #     self.fis_sim.compute()
    #     output = self.raster_nodata
    #     self.last_explainable_data = None
    #     if 'risk' not in self.fis_sim.output:
    #         self.failed.append((input_kwargs, ))
    #     else:
    #         output = self.fis_sim.output['risk']
    #         self.last_explainable_data = self.fis_sim.last_explainable_data
    #     return output


    def run_single_preprocessed(self, ch, pa, si):
        cache_id = self.get_cache_id_for_input(ch, pa, si)
        if self.cache and cache_id in self.loaded_cache_db.keys():
            output = self.loaded_cache_db[cache_id]['output']
            explainable_data = self.loaded_cache_db[cache_id]['explainable_data']
            return output, explainable_data
        print(f'Not cached {cache_id}')
        self.fis_sim.input['ch'] = ch
        self.fis_sim.input['pa'] = pa
        self.fis_sim.input['si'] = si
        self.fis_sim.compute()
        output = self.raster_nodata
        self.last_explainable_data = None
        if 'risk' not in self.fis_sim.output:
            self.failed.append(({'ch': ch, 'pa': pa, 'si': si},))
        else:
            output = self.fis_sim.output['risk']
            self.last_explainable_data = self.fis_sim.last_explainable_data
        return output, self.last_explainable_data.copy()


if __name__ == '__main__':
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

    # fis = BioRiskPlusFIS(cache=True, sri_rounding=4)
    # fis.prepare_risk_cache_db()
    import pickle
    # with open(RISK_FUZZY_CACHED_FILE, 'rb') as f:
    #     data = pickle.load(f)
    # import ipdb; ipdb.set_trace()
    # fixed_data = {}
    # for k, v in data.items():
    #     chs, pa, si = k.split('_')
    #     ch = np.float64(chs)
    #     ch_rounded = np.round(ch, decimals=4)
    #     # Create cache key
    #     cache_key = f"{ch_rounded:.4f}_{pa}_{si}"
    #     fixed_data[cache_key] = v
    # with open(RISK_FUZZY_CACHED_FILE.replace('.json','.pkl'), 'wb') as f:
    #     pickle.dump(fixed_data, f)

    # with open(RISK_FUZZY_CACHED_FILE.replace('.json','.pkl'), 'rb') as f:
    #     data = pickle.load(f)

    # print(len(data.keys()))
