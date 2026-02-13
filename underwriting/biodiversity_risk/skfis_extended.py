
from skfuzzy import control as ctrl


class ExplainableControlSystemSimulation(ctrl.ControlSystemSimulation):
    def __init__(self, control_system, clip_to_bounds=True, cache=True,
                 flush_after_run=1000, lenient=True):
        super().__init__(control_system, clip_to_bounds, cache, flush_after_run, lenient)
        self.explainable_data = {}  # Dictionary to store rule activations


    def get_rules_string_by_id_list(self, rule_ids):
        rules_str_list = []
        for rule_idx, rule in enumerate(self.ctrl.rules):
            if rule_idx in rule_ids:
                rule_str = f'IF {rule.antecedent} THEN {",".join([str(c) for c in rule.consequent])}'
                rules_str_list.append(rule_str)
        return rules_str_list

    def get_computation_explainability_data(self):
        """
        Returns:
            dict: Dictionary with rule index as key and (rule_text, firing_strength) as value and other explainability data
        """
        if next(self.ctrl.consequents).output[self] is None:
            raise ValueError("Call compute method first.")

        # for term in fuzzy_var.terms.values():
        activations = {}
        no_activations = {}

        for rule_idx, rule in enumerate(self.ctrl.rules):
            firing = rule.aggregate_firing[self]
            fire_activations_dict = no_activations
            if firing > 0:
                fire_activations_dict = activations

            # self.antecedent, cons,
            fire_activations_dict[rule_idx] = {
                'rule': f'IF {rule.antecedent} THEN {",".join([str(c) for c in rule.consequent])}',
                'activation': rule.aggregate_firing[self]
            }
        sorted_activations = dict(
            sorted(activations.items(),
                key=lambda item: item[1]['activation'],
                reverse=True)
        )
        xpl_data = {
            'activated_rules': sorted_activations
        }
        return xpl_data
    def _reset_simulation(self):
        self.explainable_data = self.get_computation_explainability_data()
        # self.print_state()
        super()._reset_simulation()
