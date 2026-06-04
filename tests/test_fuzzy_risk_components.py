import unittest
import random
import time

import numpy as np

from risk_framework.biodiversity_risk.bio_risk_fuzzy import BioRiskPlusFIS


class TestBioRiskPlusFISComponents(unittest.TestCase):
    """Tests for BioRiskPlusFIS components."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.lowest_risk =  0.11444
        self.highest_risk = 0.94583
        self.ch_raster = np.array([
            [0, 1,  0.5,   0],
            [0.5, 0,  1, 0.5],
            [1, 0.5,  0,   1]
        ], dtype=np.float32)
        self.pa_raster = np.array([
            [0, 1,  0, 0],
            [0, 0,  1, 0],
            [1, 0,  0, 1]
        ], dtype=np.float32)

        self.sri_raster = np.array([
            [0.1,   1,  0.5,   0.45],
            [0.25,   0,    1, 0.75],
            [1,   0.5,    0.65, 0.1]
        ], dtype=np.float32)

        self.hfi_raster = np.array([
            [0,   4,  0,   10],
            [4,   0,    7, 30],
            [20,   40,    0, 50]
        ], dtype=np.int16)


        self.fis = BioRiskPlusFIS(cache=False)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_map_ch_fuzzy_label_to_crisp_produces_correct_mapping(self):
        self.ch_raster = np.array([
            [0, 1,  0.5,   -9999],
            [-9999, 0,  1,   0.5],
        ], dtype=np.float64)
        ch_raster = self.fis.map_ch_fuzzy_label_to_crisp(self.ch_raster)
        expected_ch_raster = np.array([
            [0.21, 1.0,  0.5,   -9999.0],
            [-9999.0, 0.21, 1, 0.50,]
        ], dtype=np.float32)
        np.testing.assert_array_almost_equal(ch_raster,expected_ch_raster, decimal=2)


    def test_fis_run_single_simple_low_risk_case(self):
        output, xl = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(0.0)),
            'pa': 0,
            'si': 1
        })
        # if all good, then should be low risk
        self.assertAlmostEqual(output, self.lowest_risk, places=2)

    def test_fis_run_single_simple_high_risk_case(self):
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': 0
        })
        np.testing.assert_almost_equal(output, 0.94, decimal=2)
        # if all bad, then should be high risk
        self.assertAlmostEqual(output, self.highest_risk, delta=0.006)


    def test_retain_explainability_data(self):
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': 0
        })
        self.assertIn('activated_rules', self.fis.fis_sim.last_explainable_data)
        self.assertIn('activated_rules', xai)

    def test_retain_explainability_data_with_cache(self):

        self.fis = BioRiskPlusFIS(cache=True)
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': 0
        })

        self.assertIsNotNone(self.fis.fis_sim.last_explainable_data)
        expected_cached_data = self.fis.fis_sim.last_explainable_data
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(0)),
            'pa': 1,
            'si': 0
        })
        self.assertNotEqual(
            list(self.fis.fis_sim.last_explainable_data['activated_rules'].keys()),
            list(expected_cached_data['activated_rules'].keys())
        )
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': 0
        })
        self.assertDictEqual(expected_cached_data, self.fis.fis_sim.last_explainable_data)

    def test_fis_run_raster_inputs_multiple_cases_simple(self):
        self.ch_raster = np.array([
            [1,     1],
            [0,     0],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [1,     1],
            [0,     0],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [0,     0],
            [1,     1],
        ], dtype=np.float64)
        expected_raster = [
            [self.highest_risk,     self.highest_risk],
            [self.lowest_risk,     self.lowest_risk],
        ]

        risk_raster = self.fis.run(self.ch_raster, self.pa_raster, self.sri_raster)
        self.assertEqual(risk_raster.shape, (2, 2))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)

    def test_fis_run_raster_inputs_multiple_cases_only_valid_mask(self):
        nd = self.fis.raster_nodata
        self.ch_raster = np.array([
            [nd,     nd],
            [1,     0],
            [0,     0],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [1,     1],
            [1,     0],
            [0,     nd],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [0,     0],
            [0,     1],
            [nd,     1],
        ], dtype=np.float64)
        expected_raster = [
            [nd,                                   nd],
            [self.highest_risk,     self.lowest_risk],
            [nd,                                   nd],
        ]
        risk_raster = self.fis.run(self.ch_raster, self.pa_raster, self.sri_raster)

        self.assertEqual(risk_raster.shape, (3, 2))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)

#uncomment and fix test once we finish the risk model
    # def _test_fis_run_raster_inputs_multiple_cases(self):
    #     self.ch_raster = np.array([
    #         [0,     0,    0,   0],
    #         [0.5, 0.5,  0.5, 0.5],
    #         [1,     1,    1,   1]
    #     ], dtype=np.float32)
    #     self.pa_raster = np.array([
    #         [0, 0,  0, 0],
    #         [0, 0,  0, 0],
    #         [1, 1,  1, 1]
    #     ], dtype=np.float32)

    #     self.sri_raster = np.array([
    #         [0.25,   0.5,    0.75, 1],
    #         [0.25,   0.5,    0.75, 1],
    #         [0.50,   0.65,    0.75, 1.]
    #     ], dtype=np.float32)
    #     expected_raster = [
    #         [0.26 , 0.26 , 0.09 , 0.09],
    #         [0.5 , 0.43 , 0.15 , 0.15],
    #         [0.9 , 0.76 , 0.75 , 0.75]
    #     ]

    #     risk_raster = self.fis.run(self.ch_raster, self.pa_raster, self.sri_raster)

    #     self.assertEqual(risk_raster.shape, (3, 4))
    #     np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)


    def test_edge_use_cases_compared_to_original_paper(self):
        original_paper_risk = (0 + 1 + 0) / 3 # only one component as bad

        ch_bad, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(0.0)),
            'pa': 0,
            'si': 1
        })
        pa_bad, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(0)),
            'pa': 1,
            'si': 1
        })
        si_bad, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(0)),
            'pa': 0,
            'si': 0
        })
        self.assertGreaterEqual(original_paper_risk, si_bad)
        self.assertGreater(pa_bad, original_paper_risk)
        self.assertGreaterEqual(original_paper_risk, ch_bad)



    def test_cache_rounded_sri_value(self):
        output1, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.24289999902248383)
        })
        output2, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.24289199902248383)
        })
        output3, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.2429)
        })


        self.assertAlmostEqual(output1, output2, places=4)
        self.assertAlmostEqual(output1, output3, places=4)



    def test_ok_rounded_sri_value_to_speed_calc(self):
        self.fis = BioRiskPlusFIS(cache=False)
        output1, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.2429)
        })
        output2, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.24289199902248383)
        })
        output3, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.24289999902248383)
        })

        output4, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 1,
            'si': np.float64(0.2420)
        })


        self.assertAlmostEqual(output1, output2, places=4)
        self.assertAlmostEqual(output1, output3, places=4)
        self.assertNotAlmostEqual(output1, output4, places=4)


    def test_ok_only_non_pa(self):
        self.fis = BioRiskPlusFIS(cache=False, include_pa=False)
        nd = self.fis.raster_nodata
        self.ch_raster = np.array([
            [1,     1],
            [0,     1],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [1,     1],
            [0,     0],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [0,     0],
            [1,     0],
        ], dtype=np.float64)
        expected_raster = [
            [nd,     nd],
            [self.lowest_risk,     self.highest_risk],
        ]

        risk_raster = self.fis.run(self.ch_raster, self.pa_raster, self.sri_raster)

        self.assertEqual(risk_raster.shape, (2, 2))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)


    def test_output_xai_rules_data_in_xai_summary_json(self):
        output, xai = self.fis.run_single_preprocessed(**{
            'ch': np.float64(self.fis.map_ch_fuzzy_label_to_crisp(1)),
            'pa': 0,
            'si': 1,
        })

        xai_data = self.fis.get_explainability_info()

        self.assertIn('xai_summary_json', xai_data)
        xai_summary_json = xai_data['xai_summary_json']

        self.assertIn('xai_meta', xai_summary_json)
        self.assertIn('xai_humam_text', xai_summary_json)
        xai_meta = xai_summary_json['xai_meta']
        xai_humam_text = xai_summary_json['xai_humam_text']
        self.assertIn(0, xai_meta)
        self.assertIn(0, xai_humam_text)
        expected_first_rule = 'IF it is Not a Protected Area AND Critical Habitat is "Unknown" AND Species Richness is "High" THEN Risk is "Low"'
        self.assertEqual(expected_first_rule, xai_humam_text[0])

    # def test_fis_evaluate_exec_time_all_cached(self):
    #     self.fis = BioRiskPlusFIS()
    #     shape=(334, 463)
    #     rows, cols = shape

    #     # ch_raster: only 0, 0.5, 1 values
    #     ch_raster = np.random.choice([0.5], size=shape).astype(np.float64)

    #     # pa_raster: only 0 or 1 values
    #     pa_raster = np.random.choice([0], size=shape, ).astype(np.float64)

    #     sri_raster = np.full(shape, 1, dtype=np.float64)
    #     start_time = time.perf_counter()
    #     risk_raster = self.fis.run(ch_raster, pa_raster, sri_raster)
    #     end_time = time.perf_counter()

    #     elapsed_time = end_time - start_time
    #     print(f"\nExecution completed in: {elapsed_time:.4f} seconds")
    #     self.assertEqual(risk_raster.shape, shape)

    # def test_fis_evaluate_exec_time(self):
    #     self.fis = BioRiskPlusFIS()
    #     shape=(334, 463)
    #     rows, cols = shape

    #     # ch_raster: only 0, 0.5, 1 values
    #     ch_raster = np.random.choice([0, 0.5, 1], size=shape, p=[0.33, 0.34, 0.33]).astype(np.float32)

    #     # pa_raster: only 0 or 1 values
    #     pa_raster = np.random.choice([0, 1], size=shape, p=[0.5, 0.5]).astype(np.float32)

    #     # sri_raster: random floats between 0 and 1
    #     sri_raster = np.random.rand(rows, cols).astype(np.float32)
    #     start_time = time.perf_counter()
    #     risk_raster = self.fis.run(ch_raster, pa_raster, sri_raster)
    #     end_time = time.perf_counter()

    #     elapsed_time = end_time - start_time
    #     print(f"\nExecution completed in: {elapsed_time:.4f} seconds")
    #     self.assertEqual(risk_raster.shape, shape)
