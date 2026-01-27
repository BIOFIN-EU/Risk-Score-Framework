import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# New Antecedent/Consequent objects hold universe variables and membership
# functions
ch = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'ch')

# Custom membership functions can be built interactively with a familiar,
# Pythonic API
ch['unknown'] = fuzz.trapmf(ch.universe, [0, 0, 0.4, 0.60])
ch['potential'] = fuzz.trimf(ch.universe, [0.2, 0.6, 0.8])
ch['likely'] = fuzz.trapmf(ch.universe, [0.50, 0.8, 1., 1.])

# # You can see how these look with .view()
ch.view()
# Get the current figure and axes
fig = plt.gcf()
ax = plt.gca()

for color, label in zip(['blue','orange','green'],['unknown', 'potential', 'likely']):
    centroid_label = fuzz.defuzz(ch.universe, ch[label].mf, 'centroid')

    # Add vertical line for centroid
    ax.axvline(x=centroid_label, color=color, linestyle='--', linewidth=2,
            label=f'Centroid: {centroid_label:.3f}')
    print(f"Centroid of '{label}' MF: {centroid_label:.3f}")

plt.show(block=True)  # This will keep the window open until you close it




# 1. When its likely:
# 1.1 Then certainty is high, therefore is not much intersection with other interpretations

# 2. When its potention:
# 2.1 - Something is labelled as "potential" when it is Potential (IFC PS6), and there is little uncertainty
# 2.2 - Something is labelled as "potential" when it is Likely (IFC PS6), and there is more uncertainty

# 3. When its Unknown:
# 3.1 label is "unknown" when its Potential (IFC PS6) and there is too much uncertainty.
