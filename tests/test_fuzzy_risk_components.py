import unittest

import numpy as np

from underwriting.biodiversity_risk.bio_risk_plus import BioRiskPlusFIS


class TestBioRiskPlusFISComponents(unittest.TestCase):
    """Tests for BioRiskPlusFIS components."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.chl_raster = np.array([
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


        self.fis = BioRiskPlusFIS()

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def _test_map_ch_fuzzy_label_to_crisp_produces_correct_mapping(self):
        ch_raster = self.fis.map_ch_fuzzy_label_to_crisp(self.chl_raster)
        expected_ch_raster = np.array([
            [0.22, 0.80,  0.50,   0.22],
            [0.50, 0.22,  0.80, 0.50],
            [0.80, 0.50,  0.22,   0.80]
        ], dtype=np.float32)
        np.testing.assert_array_almost_equal(ch_raster,expected_ch_raster, decimal=2)


    def test_fis_run_single_simple_low_risk_case(self):
        output = self.fis.run_single(**{
            'ch': 0,
            'pa': 0,
            'si': 1
        })
        # if all good, then should be low risk
        self.assertAlmostEqual(output, 0.09, places=2)

    def test_fis_run_single_simple_high_risk_case(self):
        output = self.fis.run_single(**{
            'ch': 1,
            'pa': 1,
            'si': 0
        })
        # if all good, then should be low risk
        self.assertAlmostEqual(output, 1., places=2)


    def test_retain_explainability_data(self):
        output = self.fis.run_single(**{
            'ch': 1,
            'pa': 1,
            'si': 0
        })
        self.assertIn('activated_rules', self.fis.fis_sim.explainable_data)

    def test_fis_run_single_simple_high_risk_case(self):

        output = self.fis.run_single(**{
            'ch': 1,
            'pa': 1,
            'si': 0
        })
        # if all bad, then should be high risk
        self.assertAlmostEqual(output, 0.90, places=1)

    def _test_fis_run_raster_inputs_multiple_cases(self):
        self.chl_raster = np.array([
            [0,     0,    0,   0],
            [0.5, 0.5,  0.5, 0.5],
            [1,     1,    1,   1]
        ], dtype=np.float32)
        self.pa_raster = np.array([
            [0, 0,  0, 0],
            [0, 0,  0, 0],
            [1, 1,  1, 1]
        ], dtype=np.float32)

        self.sri_raster = np.array([
            [0.25,   0.5,    0.75, 1],
            [0.25,   0.5,    0.75, 1],
            [0.50,   0.65,    0.75, 1.]
        ], dtype=np.float32)
        expected_raster = [
            [0.26 , 0.26 , 0.09 , 0.09],
            [0.5 , 0.43 , 0.15 , 0.15],
            [0.9 , 0.76 , 0.75 , 0.75]
        ]

        risk_raster = self.fis.run(self.chl_raster, self.pa_raster, self.sri_raster)

        self.assertEqual(risk_raster.shape, (3, 4))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)


    def test_edge_use_cases_compared_to_original_paper(self):
        original_paper_risk = (1 + 0 + 0) / 3 # only one component as bad

        ch_bad = self.fis.run_single(**{
            'ch': 1,
            'pa': 0,
            'si': 1
        })
        pa_bad = self.fis.run_single(**{
            'ch': 0,
            'pa': 1,
            'si': 1
        })
        si_bad = self.fis.run_single(**{
            'ch': 0,
            'pa': 0,
            'si': 0
        })
        # import ipdb; ipdb.set_trace()
        self.assertGreaterEqual(original_paper_risk, si_bad)
        self.assertGreater(pa_bad, original_paper_risk)
        self.assertGreaterEqual(original_paper_risk, ch_bad)

