import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

default_score_names = ['low', 'medium-low', 'medium', 'medium-high', 'high']
get_rates_uod = lambda: np.arange(0, 1.01, 0.01)
# use auto-tri mf as a base, but replace left/right corners with trapezoidals
risk_var = ctrl.Consequent(get_rates_uod(), 'risk')

risk_var.automf(5, names=default_score_names)
risk_var['low'] = fuzz.trapmf(risk_var.universe, [0, 0, 0.1, 0.25])
# risk_var['high'] = fuzz.trapmf(risk_var.universe, [0.8, 0.95, 1., 1.])
risk_var['high'] = fuzz.trapmf(risk_var.universe, [0.85, 0.95, 1., 1.])
# risk_var['high'] = fuzz.trapmf(risk_var.universe, [0.75, 0.9, 1., 1.])
# risk_var['high'] = fuzz.trimf(risk_var.universe, [0.75, 1., 1.])
# risk_var['high'] = fuzz.trimf(risk_var.universe, [0.8, 1., 1.])

# # You can see how these look with .view()
risk_var.view()
# Get the current figure and axes
fig = plt.gcf()
ax = plt.gca()

for color, label in zip(['blue','orange','green', 'red', 'purple'], default_score_names):
    # defz_method = 'centroid'
    # defz_method = 'bisector'
    # defz_method = 'mom'
    # defz_method = 'som'
    defz_method = 'centroid'
    centroid_label = fuzz.defuzz(risk_var.universe, risk_var[label].mf, defz_method)
    # centroid_label = fuzz.defuzz(ch.universe, ch[label].mf, 'centroid')

    # Add vertical line for centroid
    ax.axvline(x=centroid_label, color=color, linestyle='--', linewidth=2,
            label=f'Centroid: {centroid_label:.3f}')
    print(f"Centroid of '{label}' MF: {centroid_label:.3f}")

plt.show(block=True)  # This will keep the window open until you close it

