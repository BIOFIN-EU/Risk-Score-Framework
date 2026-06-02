import unittest
import numpy as np

from risk_framework.management_actions.priority_models import MAPriorityModel


class TestMAPriorityModelComponents(unittest.TestCase):
    """Tests for MAPriorityModel components."""

    def setUp(self):
        """Set up test fixtures with 2x2 rasters (0-1 normalized values)."""
        # Biodiversity risk raster (0-1)
        self.biorisk_raster = np.array([
            [-9999, 0.30],   # Pixel (0,0): nodata, (0,1): low risk
            [0.50, 0.90]     # Pixel (1,0): medium risk, (1,1): high risk
        ], dtype=np.float64)

        # Climate resilience raster (0-1)
        self.resilience_raster = np.array([
            [0.80, 0.50],   # Pixel (0,0): high resilience, (0,1): medium resilience
            [0.20, -9999]   # Pixel (1,0): low resilience, (1,1): nodata
        ], dtype=np.float64)

        self.model = MAPriorityModel(
            risk_thresholds={
                'low': 0.33,
                'medium': 0.66,
                'high': 1.0,
            },
            resilience_thresholds={
                'low': 0.33,
                'medium': 0.66,
                'high': 1.0,
            }
        )

    def tearDown(self):
        """Tear down test fixtures."""
        pass

    def test_model_run_raster_inputs_2x2(self):
        """Test model run with 2x2 raster inputs."""
        priority_raster = self.model.run(
            self.biorisk_raster,
            self.resilience_raster
        )

        # Check shape
        self.assertEqual(priority_raster.shape, (2, 2))

        # Expected values based on valid pixel overlap:
        # Pixel (0,0): risk=nodata, resilience=0.80 -> nodata
        # Pixel (0,1): risk=0.30 (low), resilience=0.50 (medium) -> PR -> category 6
        # Pixel (1,0): risk=0.50 (medium), resilience=0.20 (low) -> Low Priority -> category 0
        # Pixel (1,1): risk=0.90 (high), resilience=nodata -> nodata

        expected_raster = np.array([
            [self.model.raster_nodata, 6],
            [0, self.model.raster_nodata]
        ], dtype=np.int16)

        # Assert entire raster
        np.testing.assert_array_equal(priority_raster, expected_raster)

    def test_all_category_combinations(self):
        """Test all 9 risk x resilience combinations return correct categories."""
        risk_high, risk_med, risk_low = 0.9, 0.5, 0.1
        res_high, res_med, res_low = 0.9, 0.5, 0.1


        # 3x3 raster: rows = risk (high, med, low), cols = resilience (high, med, low)
        biorisk_raster = np.array([
            [risk_high, risk_high, risk_high],
            [risk_med, risk_med, risk_med],
            [risk_low, risk_low, risk_low]
        ], dtype=np.float64)

        resilience_raster = np.array([
            [res_high, res_med, res_low],
            [res_high, res_med, res_low],
            [res_high, res_med, res_low]
        ], dtype=np.float64)

        AP_I, AP_II, PP = 1, 2, 3
        AR_I, AR_II, PR = 4, 5, 6
        LOW_PRIORITY = 0
        # Expected categories based on matrix
        # Row0: High risk, Col0: High res -> AP I, Col1: Med res -> AR I, Col2: Low res -> Low Priority
        # Row1: Med risk,  Col0: High res -> AP II, Col1: Med res -> AR II, Col2: Low res -> Low Priority
        # Row2: Low risk,  Col0: High res -> PP,  Col1: Med res -> PR,  Col2: Low res -> Low Priority
        expected_raster = np.array([
            [AP_I, AR_I, LOW_PRIORITY],
            [AP_II, AR_II, LOW_PRIORITY],
            [PP, PR, LOW_PRIORITY]
        ], dtype=np.int16)

        result = self.model.run(biorisk_raster, resilience_raster)
        np.testing.assert_array_equal(result, expected_raster)
