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

    def test_fis_run_simple_case(self):
        self.fis.setup()

        output = self.fis.run(**{
            'ch': 1,
            'pa': 1,
            'si': 0
        })
        # if all high, then should be high risk
        self.assertAlmostEqual(output, 0.91, places=1)


    def _analyze_failed_inputs_simple(self, failed_inputs_list):
        """Show only crisp values and most representative MFs"""

        print("=" * 60)
        print("FAILED INPUTS - CRISP VALUES & DOMINANT MEMBERSHIP FUNCTIONS")
        print("=" * 60)

        for i, item in enumerate(failed_inputs_list):
            input_dict = item[0]
            ch_val = input_dict['ch']
            pa_val = input_dict['pa']
            si_val = input_dict['si']

            # Determine dominant CH MF
            if ch_val == 0:
                ch_mf = "unknown"
            elif ch_val == 0.5:
                # 0.5 is at the peak of 'potential' MF (0.2, 0.6, 0.8)
                ch_mf = "potential"
            elif ch_val == 1:
                ch_mf = "likely"
            else:
                ch_mf = "unknown/potential"

            # Determine dominant PA MF
            pa_mf = "protected" if pa_val == 1 else "unprotected"

            # Determine dominant SI MF (5 autoMF functions evenly spaced 0-1)
            if si_val <= 0.2:
                si_mf = "low"
            elif si_val <= 0.4:
                si_mf = "medium-low"
            elif si_val <= 0.6:
                si_mf = "medium"
            elif si_val <= 0.8:
                si_mf = "medium-high"
            else:
                si_mf = "high"

            print(f"Input {i+1:2d}: ch={ch_val:4.1f} ({ch_mf:9s}) | "
                f"pa={pa_val:1.0f} ({pa_mf:11s}) | "
                f"si={si_val:5.2f} ({si_mf:11s})")

        print("=" * 60)
        print("\nMISSING RULE PATTERNS (Grouped by frequency):")
        print("-" * 40)

        # Group and count patterns
        patterns = {}
        for item in failed_inputs_list:
            input_dict = item[0]
            ch_val = input_dict['ch']
            pa_val = input_dict['pa']
            si_val = input_dict['si']

            # Get MFs
            ch_mf = "unknown" if ch_val == 0 else "potential" if ch_val == 0.5 else "likely"
            pa_mf = "protected" if pa_val == 1 else "unprotected"
            si_mf = "high" if si_val > 0.8 else "medium-high" if si_val > 0.6 else "medium" if si_val > 0.4 else "medium-low" if si_val > 0.25 else "low"

            pattern = f"ch={ch_mf}, pa={pa_mf}, si={si_mf}"
            patterns[pattern] = patterns.get(pattern, 0) + 1

        # Show patterns sorted by frequency
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"Pattern: {pattern:50s} | Count: {count:2d}")

        print("\n" + "=" * 60)
        print("SUGGESTED RULES TO ADD:")
        print("-" * 40)

        unique_patterns = set(patterns.keys())
        for i, pattern in enumerate(sorted(unique_patterns)):
            ch_part = pattern.split(',')[0].replace('ch=', '').strip()
            pa_part = pattern.split(',')[1].replace('pa=', '').strip()
            si_part = pattern.split(',')[2].replace('si=', '').strip()

            # Suggest a consequent - you need to decide what risk level makes sense
            print(f"Rule {i+1}: IF ch IS {ch_part} AND pa IS {pa_part} AND si IS {si_part} THEN risk IS ???")

    def test_control_space_surface_plot_and_rules_activation(self):
        self.fis.setup()
        si_values = np.arange(0, 1.01, 0.05)  # 0 to 1 in steps of 0.05
        ch_values = np.array([0, 0.5, 1])  # Only these discrete values for ch
        pa_fixed = 1  # Fixed value for protected area

        # Create meshgrid for the two varying variables
        ch_mesh, si_mesh = np.meshgrid(ch_values, si_values)
        z = np.zeros_like(ch_mesh, dtype=float)

        # Collect the control surface
        for i in range(len(si_values)):
            for j in range(len(ch_values)):
                output = self.fis.run(**{
                    'ch': ch_mesh[i, j],
                    'pa': pa_fixed,
                    'si': si_mesh[i, j]
                })
                z[i, j] = output
        import json


        self._analyze_failed_inputs_simple(self.fis.failed)
        print(json.dumps(self.fis.failed, indent=4))
        # Plot the result
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D


        self.fis.si_var.view()
        plt.show()

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Plot surface - note that ch only has 3 discrete values
        surf = ax.plot_surface(ch_mesh, si_mesh, z, rstride=1, cstride=1,
                            cmap='viridis', linewidth=0.4, antialiased=True)

        # Add contour projections
        cset = ax.contourf(ch_mesh, si_mesh, z, zdir='z', offset=-0.2,
                        cmap='viridis', alpha=0.5)
        cset = ax.contourf(ch_mesh, si_mesh, z, zdir='x', offset=-0.5,
                        cmap='viridis', alpha=0.5)
        cset = ax.contourf(ch_mesh, si_mesh, z, zdir='y', offset=1.2,
                        cmap='viridis', alpha=0.5)

        # Set axis labels
        ax.set_xlabel('CH (0, 0.5, or 1)')
        ax.set_ylabel('SI (0 to 1)')
        ax.set_zlabel('Risk Output')
        ax.set_title(f'FIS Control Surface (PA = {pa_fixed})')

        # Set axis limits
        ax.set_xlim([-0.1, 1.1])
        ax.set_ylim([-0.05, 1.05])
        ax.set_zlim([-0.2, 1.1])

        # Add colorbar
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Risk')

        ax.view_init(30, 200)
        plt.tight_layout()
        plt.show()

        # import ipdb; ipdb.set_trace()
        print('a')


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

