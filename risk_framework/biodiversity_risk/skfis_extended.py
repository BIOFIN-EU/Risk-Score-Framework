import numpy as np

from skfuzzy import control as ctrl
from skfuzzy.control.controlsystem import CrispValueCalculator
from skfuzzy.control.term import TermAggregate, Term


class ExplainableControlSystemSimulation(ctrl.ControlSystemSimulation):
    def __init__(self, control_system, clip_to_bounds=True, cache=True,
                 flush_after_run=1000, lenient=True):
        super().__init__(control_system, clip_to_bounds, cache, flush_after_run, lenient)
        self.last_explainable_data = None  # Dictionary to store rule activations
        self.si_rounding = 2


    def _update_unique_id(self):
        """
        Unique hash of this control system including a specific set of inputs.

        Generated at runtime from the system state. Used as key to access data
        from `StatePerSimulation` objects, enabling multiple runs.
        """
        # The string to be hashed is the concatenation of:
        #  * the control system ID, which is independent of inputs
        #  * hash of the current input OrderedDict

        # Caching only enabled if no array inputs
        if not self._array_inputs:
            # Simple hashes and Python ids are fast and serve our purposes.
            tmp_input_dict = self._get_inputs().copy()
            if tmp_input_dict['si'] is not None:
                tmp_input_dict['si'] = np.round(tmp_input_dict['si'], decimals=self.si_rounding)
            self.unique_id = (str(id(self.ctrl)) +
                              str(hash(tmp_input_dict.__repr__())))

    def compute(self):
        """
        Compute the fuzzy system.
        """
        self.input._update_to_current()
        self.last_explainable_data = None  # Dictionary to store rule activations

        # Must clear downstream calculations for repeated runs
        if self._array_inputs:
            self.cache = False
            self._clear_outputs()
        # Shortcut with lookup if this calculation was done before
        if self.cache is not False and self.unique_id in self._calculated:
            # print(f'has cache for: {self.unique_id}')
            for consequent in self.ctrl.consequents:
                if consequent.output[self] is not None:
                    self.output[consequent.label] = consequent.output[self]
                    self.last_explainable_data = self.get_computation_explainability_data()
                    # print(f'has cached output: {self.output[consequent.label]}')
            return
        # si_round = np.round(self._get_inputs()['si'], decimals=self.si_rounding)
        # print(f'NO cache for: {self._get_inputs()["si"]}')
        # If we get here, cache is disabled OR the inputs are novel. Compute!

        # Check if any fuzzy variables lack input values and fuzzify inputs
        for antecedent in self.ctrl.antecedents:
            if antecedent.input[self] is None:
                raise ValueError("All antecedents must have input values!")
            CrispValueCalculator(antecedent, self).fuzz(antecedent.input[self])

        # Calculate rules, taking inputs and accumulating outputs
        first = True
        for rule in self.ctrl.rules:
            # Clear results of prior runs from Terms if needed.
            if first:
                for c in rule.consequent:
                    c.term.membership_value[self] = None
                    c.activation[self] = None
                first = False
            self.compute_rule(rule)

        # Collect the results and present them as a dict
        self.output = self.defuzz_consequents()
        self.last_explainable_data = self.get_computation_explainability_data()

        # Make note of this run so we can easily find it again
        if self.cache is not False:
            self._calculated.append(self.unique_id)
        else:
            # Reset StatePerSimulations
            self._reset_simulation()

        # Increment run number
        self._run += 1
        if self._run % self._flush_after_run == 0:
            self._reset_simulation()


    def get_term_human_text(self, term):
        """Convert a fuzzy term (antecedent or consequent) to human readable text"""
        var_label = term.parent.label
        value_label = term.label

        # Map variable labels to human readable names
        var_name_map = {
            'ch': 'Critical Habitat',
            'pa': 'Protected Area',
            'si': 'Species Richness',
            'risk': 'Risk'
        }

        # Special handling for Protected Area
        if var_label == 'pa':
            if value_label == 'protected':
                return 'it is a Protected Area'
            elif value_label == 'unprotected':
                return 'it is Not a Protected Area'

        # For other variables, capitalize the value label
        human_value = value_label.capitalize()
        human_var = var_name_map.get(var_label, var_label)

        return f'{human_var} is "{human_value}"'

    def get_antecedent_human_text(self, antecedent):
        """Recursively convert antecedent to human readable text"""
        if isinstance(antecedent, Term):
            # Base case: reached a Term
            return self.get_term_human_text(antecedent)
        elif isinstance(antecedent, TermAggregate):
            # Recursive case: combine left and right parts
            left_text = self.get_antecedent_human_text(antecedent.term1)
            right_text = self.get_antecedent_human_text(antecedent.term2)

            is_pa_on_right = isinstance(antecedent.term2, Term) and antecedent.term2.parent.label == 'pa'
            # Check if term2 is PA (Protected Area) and swap if needed
            if is_pa_on_right:
                left_text, right_text = right_text, left_text

            # Combine based on the kind (AND/OR)
            kind_text = str(antecedent.kind).upper()
            return f'{left_text} {kind_text} {right_text}'

    def get_consequent_human_text(self, consequent):
        """Convert consequent to human readable text"""
        # consequent is a list, but should have only one item for our model
        term = consequent[0].term
        return self.get_term_human_text(term)

    def get_rules_string_by_id_list(self, rule_ids):
        rules_str_list = []
        for rule_idx, rule in enumerate(self.ctrl.rules):
            if rule_idx in rule_ids:
                rule_str = f'IF {rule.antecedent} THEN {",".join([str(c) for c in rule.consequent])}'
                rules_str_list.append(rule_str)
        return rules_str_list


    def get_all_rules_id_components_map(self):
        rules_id_str = {}
        for rule_idx, rule in enumerate(self.ctrl.rules):
            rule_str = f'IF {rule.antecedent} THEN {",".join([str(c) for c in rule.consequent])}'
            rules_id_str[rule_idx] = rule_str

        return rules_id_str

    def get_all_rules_id_components_map_humam(self):
        rules_id_str = {}
        for rule_idx, rule in enumerate(self.ctrl.rules):

            ant_text = self.get_antecedent_human_text(rule.antecedent)
            # Get human readable consequent text
            cons_text = self.get_consequent_human_text(rule.consequent)

            # rule_str = f'IF {rule.antecedent} THEN {",".join([str(c) for c in rule.consequent])}'
            rule_str = f'IF {ant_text} THEN {cons_text}'
            rules_id_str[rule_idx] = rule_str

        return rules_id_str

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
                'rule_id': rule_idx,
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
    # def _reset_simulation(self):
    #     self.explainable_data = self.get_computation_explainability_data()
    #     # self.print_state()
    #     super()._reset_simulation()
