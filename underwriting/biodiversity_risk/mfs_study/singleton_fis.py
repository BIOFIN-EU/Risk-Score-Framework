
import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


ch_var = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'ch')

ch_var.automf(3, names=['low', 'medium', 'high'])

# pa_var = ctrl.Antecedent(np.array([0., 0, 1, 1.]), 'pa')
# pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
# pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)



pa_var =  ctrl.Antecedent(np.arange(0, 1.001, 0.001), 'pa')
pa_var['unprotected'] = fuzz.trimf(pa_var.universe, [0, 0, 0.001])
pa_var['protected'] = fuzz.trimf(pa_var.universe, [0.999, 1, 1])

# pa_var = ctrl.Antecedent(np.array([0., 0.01, 0.99, 1.]), 'pa')
# pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
# pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)




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
fis = ctrl.ControlSystem(rules)
fis_sim = ctrl.ControlSystemSimulation(fis)
# fis_sim.input['ch'] = 0.5
# fis_sim.input['pa'] = 0
# out == 0.49 ~= 0.5

fis_sim.input['ch'] = 0.25
fis_sim.input['pa'] = 0
# out == 0.49 ~= 0.5

# Crunch the numbers
fis_sim.compute()
print(fis_sim.output['out'])
print(fis_sim.print_state())
# import ipdb; ipdb.set_trace()
pa_var.view(sim=fis_sim)
ch_var.view(sim=fis_sim)
out_var.view(sim=fis_sim)

plt.show(block=True)  # This will keep the window open until you close it
