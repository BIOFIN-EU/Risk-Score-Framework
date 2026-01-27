import unittest

import numpy as np


import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl





class TestSingletonFIS(unittest.TestCase):
    """Tests for a singleton fis package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        ch_var = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'ch')
        self.ch_var = ch_var
        ch_var.automf(3, names=['low', 'medium', 'high'])

        # pa_var = ctrl.Antecedent(np.array([0., 0, 1, 1.]), 'pa')
        # pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
        # pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)



        # pa_var =  ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'pa')
        # pa_var['unprotected'] = fuzz.trimf(pa_var.universe, [0, 0, 0])
        # pa_var['protected'] = fuzz.trimf(pa_var.universe, [1, 1, 1])

        pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
        pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
        pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


        # # You can see how these look with .view()
        # ch_var.view()
        # pa_var.automf(2, names=['unprotected', 'protected'])


        out_var = ctrl.Consequent(np.arange(0, 1.1, 0.1), 'out')
        out_var.automf(3, names=['low', 'medium', 'high'])

        rule1 = ctrl.Rule(ch_var['low'] & pa_var['unprotected'], out_var['low'])
        rule2 = ctrl.Rule(ch_var['medium'] & pa_var['unprotected'], out_var['medium'])
        rule3 = ctrl.Rule(ch_var['high'] &  pa_var['unprotected'], out_var['high'])

        rule4 = ctrl.Rule(ch_var['low'] & pa_var['protected'], out_var['high'])
        rule5 = ctrl.Rule(ch_var['medium'] & pa_var['protected'], out_var['high'])
        rule6 = ctrl.Rule(ch_var['high'] &  pa_var['protected'], out_var['high'])

        rules = [rule1, rule2, rule3, rule4, rule5, rule6]
        self.fis = ctrl.ControlSystem(rules)
        self.fis_sim = ctrl.ControlSystemSimulation(self.fis, flush_after_run=True)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_properly_activation_r2_medium_for_false_singleton(self):
        self.fis_sim.input['ch'] = 0.5
        self.fis_sim.input['pa'] = 0
        # out == 0.49 ~= 0.5

        self.fis_sim.compute()
        np.testing.assert_almost_equal(self.fis_sim.output['out'], 0.49, decimal=2)

    def test_properly_activation_r1_r2_medium_low_for_false_singleton(self):
        self.fis_sim.input['ch'] = 0.25
        self.fis_sim.input['pa'] = 0
        # out == 0.44

        self.fis_sim.compute()
        np.testing.assert_almost_equal(self.fis_sim.output['out'], 0.44, decimal=2)

        # print(fis_sim.output['out'])
        # print(fis_sim.print_state())
        # # import ipdb; ipdb.set_trace()
        # out_var.view(sim=fis_sim)
        # np.testing.assert_array_almost_equal(self.fis.ch_raster,expected_ch_raster, decimal=2)


