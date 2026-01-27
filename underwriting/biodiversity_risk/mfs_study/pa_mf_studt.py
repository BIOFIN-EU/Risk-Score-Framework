import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# New Antecedent/Consequent objects hold universe variables and membership
# functions


# pa_var = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'pa')


# pa_var['unprotected'] = fuzz.trimf(pa_var.universe, [0, 0, 0])
# pa_var['protected'] = fuzz.trimf(pa_var.universe, [1, 1, 1])


# # # You can see how these look with .view()
# pa_var.view()
# # Get the current figure and axes
# fig = plt.gcf()
# ax = plt.gca()

# for color, label in zip(['blue','orange'],['unprotected', 'protected']):
#     centroid_label = fuzz.defuzz(pa_var.universe, pa_var[label].mf, 'centroid')
#     print()
#     # Add vertical line for centroid
#     ax.axvline(x=centroid_label, color=color, linestyle='--', linewidth=2,
#             label=f'Centroid: {centroid_label:.3f}')
#     print(f"Centroid of '{label}' MF: {centroid_label:.3f}")

# plt.show(block=True)  # This will keep the window open until you close it




# pa_var = ctrl.Antecedent(np.array([0., 0, 1, 1.]), 'pa')


# pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
# pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


# # # You can see how these look with .view()
# pa_var.view()
# # Get the current figure and axes
# fig = plt.gcf()
# ax = plt.gca()

# for color, label in zip(['blue','orange'],['unprotected', 'protected']):
#     centroid_label = fuzz.defuzz(pa_var.universe, pa_var[label].mf, 'lom')
#     # Add vertical line for centroid
#     ax.axvline(x=centroid_label, color=color, linestyle='--', linewidth=2,
#             label=f'Centroid: {centroid_label:.3f}')
#     print(f"Centroid of '{label}' MF: {centroid_label:.3f}")

# plt.show(block=True)  # This will keep the window open until you close it





pa_var = ctrl.Antecedent(np.array([0., 0.001, 0.999, 1.]), 'pa')
pa_var['unprotected'] = np.array([1, 0, 0, 0], dtype=np.float32)
pa_var['protected'] = np.array([0, 0, 0, 1], dtype=np.float32)


# # You can see how these look with .view()
pa_var.view()
# Get the current figure and axes
fig = plt.gcf()
ax = plt.gca()

for color, label in zip(['blue','orange'],['unprotected', 'protected']):
    centroid_label = fuzz.defuzz(pa_var.universe, pa_var[label].mf, 'centroid')
    # Add vertical line for centroid
    ax.axvline(x=centroid_label, color=color, linestyle='--', linewidth=2,
            label=f'Centroid: {centroid_label:.3f}')
    print(f"Centroid of '{label}' MF: {centroid_label:.3f}")

plt.show(block=True)  # This will keep the window open until you close it
