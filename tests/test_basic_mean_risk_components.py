import unittest
import time

import numpy as np

from risk_framework.biodiversity_risk.base_risk_model import BioRiskBasic


class TestBioRiskBasicComponents(unittest.TestCase):
    """Tests for BioRiskBasic components."""

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

        self.model = BioRiskBasic(cache=False)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_model_run_raster_inputs_multiple_cases_simple(self):
        self.ch_raster = np.array([
            [1,     0.75],
            [0.25,     0],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [0,     0],
            [0,     0],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [1,     0.25],
            [0.75,     1],
        ], dtype=np.float64)
        expected_raster = [
            [0.5,     0.75],
            [0.25,     0],
        ]
        self.model.include_pa = False

        risk_raster = self.model.run(self.ch_raster, self.pa_raster, self.sri_raster)
        self.assertEqual(risk_raster.shape, (2, 2))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)


    def test_model_run_raster_inputs_multiple_cases_simple_with_pa(self):
        self.ch_raster = np.array([
            [1,     0.75],
            [0.25,     0],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [0,     0],
            [1,     0],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [1,     0.25],
            [0.75,     1],
        ], dtype=np.float64)
        expected_raster = [
            [0.33,     0.5],
            [0.5,     0],
        ]
        self.model.include_pa = True

        risk_raster = self.model.run(self.ch_raster, self.pa_raster, self.sri_raster)
        self.assertEqual(risk_raster.shape, (2, 2))
        np.testing.assert_array_almost_equal(risk_raster,expected_raster, decimal=2)

    def test_model_returns_correct_xai_data(self):
        self.ch_raster = np.array([
            [1,     0.75],
            [0.25,     0],
        ], dtype=np.float64)
        self.pa_raster = np.array([
            [0,     0],
            [0,     0],
        ], dtype=np.float64)

        self.sri_raster = np.array([
            [1,     0.25],
            [0.75,     1],
        ], dtype=np.float64)

        risk_raster = self.model.run(self.ch_raster, self.pa_raster, self.sri_raster)
        xai_data = self.model.get_explainability_info()
        self.assertIn('xai_raster', xai_data)

        xai_raster = xai_data['xai_raster']
        self.assertEqual(xai_raster.shape, risk_raster.shape)

        self.assertIn('xai_summary_json', xai_data)
        xai_summary_json = xai_data['xai_summary_json']
        self.assertIn('xai_meta', xai_summary_json)
        self.assertIn('xai_humam_text', xai_summary_json)
