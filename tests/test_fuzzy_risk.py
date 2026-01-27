import unittest

import numpy as np

from underwriting.biodiversity_risk.bio_risk_plus import BioRiskPlusFIS, BioRiskPlusExtendedFIS


class TestBioRiskPlusFIS(unittest.TestCase):
    """Tests for BioRiskPlusFIS package."""

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
            [0.1,   1,  0.5,   0],
            [0.5,   0,    1, 0.5],
            [1,   0.5,    0, 0.1]
        ], dtype=np.float32)
        self.hfi_raster = np.array([
            [0,   4,  0,   10],
            [4,   0,    7, 30],
            [20,   40,    0, 50]
        ], dtype=np.int16)


        self.fis = BioRiskPlusFIS(self.chl_raster, self.pa_raster, self.sri_raster)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_map_ch_fuzzy_label_to_crisp_produces_correct_mapping(self):
        """Test the common function."""
        self.fis.setup()
        expected_ch_raster = np.array([
            [0.25, 0.81,  0.53,   0.25],
            [0.53, 0.25,  0.81, 0.53],
            [0.81, 0.53,  0.25,   0.81]
        ], dtype=np.float32)
        np.testing.assert_array_almost_equal(self.fis.ch_raster,expected_ch_raster, decimal=2)


class TestBioRiskPlusExtendedFIS(unittest.TestCase):
    """Tests for BioRiskPlusExtendedFIS package."""

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
            [0.1,   1,  0.5,   0],
            [0.5,   0,    1, 0.5],
            [1,   0.5,    0, 0.1]
        ], dtype=np.float32)
        self.hfi_raster = np.array([
            [0,   4,  0,   10],
            [4,   0,    7, 30],
            [20,   40,    0, 50]
        ], dtype=np.int16)


        self.fis = BioRiskPlusExtendedFIS(self.chl_raster, self.pa_raster, self.sri_raster, self.hfi_raster)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_map_ch_fuzzy_label_to_crisp_produces_correct_mapping(self):
        """Test the common function."""
        self.fis.setup()
        expected_ch_raster = np.array([
            [0.25, 0.81,  0.53,   0.25],
            [0.53, 0.25,  0.81, 0.53],
            [0.81, 0.53,  0.25,   0.81]
        ], dtype=np.float32)
        np.testing.assert_array_almost_equal(self.fis.ch_raster,expected_ch_raster, decimal=2)

