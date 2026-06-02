"""
Unit tests for BaseCRModel (Climate Resilience Model based on Noah et al. 2021).
"""

import unittest
import numpy as np

from risk_framework.climate_resilience.base_cr_model import BaseCRModel


class TestBaseCRModelComponents(unittest.TestCase):
    """Tests for BaseCRModel components."""

    def setUp(self):
        """Set up test fixtures with 2x2 rasters (0-1 normalized values)."""
        # 2x2 test rasters
        self.current = np.array([
            [1.00, 0.00],
            [0.50, -9999]
        ], dtype=np.float64)

        self.ssp245_2040 = np.array([
            [0.90, 0.80],
            [0.70, 0.60]
        ], dtype=np.float64)

        self.ssp245_2060 = np.array([
            [0.85, 0.75],
            [0.65, 0.55]
        ], dtype=np.float64)

        self.ssp585_2040 = np.array([
            [0.80, 0.70],
            [0.50, 0.40]
        ], dtype=np.float64)

        self.ssp585_2060 = np.array([
            [0.70, 0.60],
            [0.40, 0.30]
        ], dtype=np.float64)

        self.model = BaseCRModel()

    def tearDown(self):
        """Tear down test fixtures."""
        pass

    def test_model_run_raster_inputs_2x2(self):
        """Test model run with 2x2 raster inputs."""
        resilience_raster = self.model.run(
            self.current,
            self.ssp245_2040,
            self.ssp245_2060,
            self.ssp585_2040,
            self.ssp585_2060
        )

        # Check shape
        self.assertEqual(resilience_raster.shape, (2, 2))

        # Expected values based on manual calculation using change normalization
        # Pixel (0,0): current=1.00, avg245=0.875, avg585=0.75
        #   resilience = min(0.4375, 0.375) = 0.375

        # Pixel (0,1): current=0.00 (valid: >=0), avg245=0.775, avg585=0.65
        #   resilience = min(0.8875, 0.825) = 0.825

        # Pixel (1,0): current=0.50, avg245=0.675, avg585=0.45
        #   resilience = min(0.5875, 0.475) = 0.475

        # Pixel (1,1): current=-9999 -> nodata, not in valid_mask -> nodata

        # Assert each pixel individually
        expected_raster = np.array([
            [0.375, 0.825],
            [0.475, self.model.raster_nodata]
        ], dtype=np.float64)

        # Assert entire raster
        np.testing.assert_array_almost_equal(resilience_raster, expected_raster, decimal=3)
