import skfuzzy as fuzz




rule_format = """
new_rules.append(ctrl.Rule(
    self.ch_var['{ch_label}'] & self.pa_var['{pa_label}'] & self.si_var['{si_label}'],
    self.risk_var['']
))
"""


rule_script = """
new_rules = []
"""
for ch_label in ['unknown', 'potential', 'likely']:
    for pa_label in ['unprotected', 'protected']:
        for si_label in reversed(['low', 'medium-low', 'medium', 'medium-high', 'high']):
            rule_script += rule_format.format(
                ch_label=ch_label,
                pa_label=pa_label,
                si_label=si_label
            )



with open('rules_script.py', 'w') as f:
    f.write(rule_script)
