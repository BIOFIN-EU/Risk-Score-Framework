import unittest

import numpy as np

from underwriting.biodiversity_risk.bio_risk_plus import BioRiskPlusFIS


class TestBioRiskPlusFIS(unittest.TestCase):
    """Tests (actually exploratory analysis) for BioRiskPlusFIS."""

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
            si_mf = "high" if si_val > 0.8 else "medium-high" if si_val > 0.6 else "medium" if si_val > 0.4 else "medium-low" if si_val >= 0.25 else "low"

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

    def _generate_surfaceplot(self, pa_fixed, map_ch_values=False):
        si_values = np.arange(0, 1.01, 0.01)  # 0 to 1 in steps of 0.05
        ch_values = np.array([0, 0.5, 1])  # Only these discrete values for ch
        ch_legend_vals = self.fis.map_ch_fuzzy_label_to_crisp(ch_values)

        # Create meshgrid for the two varying variables
        ch_mesh, si_mesh = np.meshgrid(ch_values, si_values)
        z = np.zeros_like(ch_mesh, dtype=float)

        # Collect the control surface
        for i in range(len(si_values)):
            for j in range(len(ch_values)):
                ch_val = ch_mesh[i, j]
                if map_ch_values:
                    ch_val = float(self.fis.map_ch_fuzzy_label_to_crisp(ch_val))
                try:
                    output = self.fis.run_single(**{
                        'ch': ch_val,
                        'pa': pa_fixed,
                        'si': si_mesh[i, j]
                    })
                except Exception as e:
                    print(e)
                    import ipdb; ipdb.set_trace()
                    print(f"{[i, j]}")
                z[i, j] = output
        import json


        # self._analyze_failed_inputs_simple(self.fis.failed)
        # print(json.dumps(self.fis.failed, indent=4))
        # Plot the result
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D

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
        title = f'FIS Control Surface (PA = {pa_fixed})'
        # if map_ch_values:
        #     title += f' - CH as {list(ch_legend_vals)}'
        ax.set_title(title)

        # Set axis limits
        ax.set_xlim([-0.1, 1.1])
        ax.set_ylim([-0.05, 1.05])
        ax.set_zlim([-0.2, 1.1])

        # Add colorbar
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Risk')

        ax.view_init(30, 125, 0)
        return ax, fig

    def _generate_combined_surfaceplot(self, pa_values=None, map_ch_values=False):
        """Generate a combined 3D plot with surfaces for multiple pa values."""
        if pa_values is None:
            pa_values = [0, 1]  # Default to pa=0 and pa=1

        si_values = np.arange(0, 1.01, 0.01)  # 0 to 1 in steps of 0.01
        ch_values = np.array([0, 0.5, 1])  # Only these discrete values for ch
        # ch_values = self.fis.map_ch_fuzzy_label_to_crisp(ch_values)

        # Create figure and axis
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.cm as cm
        from matplotlib.colors import LinearSegmentedColormap

        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection='3d')



            # Create a base blue-to-red colormap
        base_cmap = cm.coolwarm

        # Create modified colormaps with different intensities/alphas
        # PA=0: lighter version (higher alpha/more transparent)
        # PA=1: full intensity version
        pa_cmap_configs = {
            0: {'alpha': 0.9, 'brightness_factor': 1.2},  # Lighter, more transparent
            1: {'alpha': 0.9, 'brightness_factor': 1.0}   # Darker, less transparent
        }

        # Function to create a lighter version of a colormap
        def lighten_cmap(cmap, factor=1.2):
            """Lighten a colormap by scaling colors towards white."""
            colors = cmap(np.linspace(0, 1, 256))
            # Lighten colors by mixing with white
            white = np.array([0.8, 0.8, 0.8, 0.8])
            lightened_colors = colors + (white - colors) * (1 - 1/factor)
            lightened_colors = np.clip(lightened_colors, 0, 1)
            return LinearSegmentedColormap.from_list(f'lightened_{cmap.name}', lightened_colors)

        # Store surfaces and their data for later use
        surfaces = []
        surface_data = []  # Store (pa_value, surface_object, min_z, max_z)

        for idx, pa_fixed in enumerate(pa_values):
            # Create meshgrid
            ch_mesh, si_mesh = np.meshgrid(ch_values, si_values)
            z = np.zeros_like(ch_mesh, dtype=float)

            # Calculate the surface for this pa value
            for i in range(len(si_values)):
                for j in range(len(ch_values)):
                    ch_val = ch_mesh[i, j]
                    if map_ch_values:
                        ch_val = float(self.fis.map_ch_fuzzy_label_to_crisp(ch_val))
                    output = self.fis.run_single(**{
                        'ch': ch_val,
                        'pa': pa_fixed,
                        'si': si_mesh[i, j]
                    })
                    z[i, j] = output

            # Get colormap configuration for this pa value
            config = pa_cmap_configs.get(pa_fixed, {'alpha': 0.7, 'brightness_factor': 1.0})

            # Create appropriate colormap
            # if config['brightness_factor'] > 1.0:
            #     cmap = lighten_cmap(base_cmap, config['brightness_factor'])
            # else:
            # cmap = cm.Greys
            cmap = cm.Greys
            cmap = 'viridis'

            # # Choose colormap based on pa value
            # if pa_fixed == 0:
            #     cmap = cm.YlOrRd
            # else:
            #     # For pa=1: blue to yellow
            #     # You can use 'viridis', 'plasma', or create custom
            #     cmap = cm.coolwarm  # Blue to red
            #     # Or for blue to yellow specifically:
            #     # cmap = cm.YlGnBu  # Yellow-green-blue

            # Plot the surface
            surf = ax.plot_surface(
                ch_mesh,
                si_mesh,
                z,
                cmap=cmap,
                rstride=1,
                cstride=1,
                linewidth=0.5,
                antialiased=True,
                # alpha=config['alpha'],  # Transparency to see through surfaces
                label=f'PA = {pa_fixed}'
            )

            surfaces.append(surf)
            surface_data.append((pa_fixed, surf, z.min(), z.max()))

        # Set axis labels
        ax.set_xlabel('CH (0, 0.5, or 1)', fontsize=12)
        ax.set_ylabel('SI (0 to 1)', fontsize=12)
        ax.set_zlabel('Risk Output', fontsize=12)
        ax.set_title(f'FIS Control Surface - Combined PA Values', fontsize=14, fontweight='bold')

        # Set axis limits
        ax.set_xlim([-0.1, 1.1])
        ax.set_ylim([-0.05, 1.05])

        # Adjust z-limits based on all data
        all_z_mins = [data[2] for data in surface_data]
        all_z_maxs = [data[3] for data in surface_data]
        z_min = min(all_z_mins) - 0.1 if min(all_z_mins) > 0 else -0.2
        z_max = max(all_z_maxs) + 0.1
        ax.set_zlim([z_min, z_max])

        # Create a custom legend
        from matplotlib.patches import Patch

        # Create color patches for the legend
        legend_elements = []
        if 0 in pa_values:
            legend_elements.append(Patch(alpha=0.7, label='PA = 0 (Bottom-surface)'))

        if 1 in pa_values:
            legend_elements.append(Patch(alpha=0.7, label='PA = 1 (Top-surface)'))

        ax.legend(handles=legend_elements, loc='upper left')


        ax.view_init(30, 125, 0)

        return ax, fig

    def test_control_sperarate_space_surface_plot_and_rules_activation(self):
        import matplotlib.pyplot as plt
        # map_ch_values = False
        # ax, fig = self._generate_surfaceplot(pa_fixed=0, map_ch_values=map_ch_values)
        # ax2, fig2 = self._generate_surfaceplot(pa_fixed=1, map_ch_values=map_ch_values)

        map_ch_values = True
        ax, fig_b = self._generate_surfaceplot(pa_fixed=0, map_ch_values=map_ch_values)
        # ax2, fig2_b = self._generate_surfaceplot(pa_fixed=1, map_ch_values=map_ch_values)
        plt.tight_layout()
        plt.show()

    def _test_control_space_combined_surface_plot_and_rules_activation(self):
        import matplotlib.pyplot as plt
        ax, fig = self._generate_combined_surfaceplot(pa_values=[0, 1], map_ch_values=True)
        plt.tight_layout()
        plt.show()
