# Managing Uncertainties of Biodiversity Risk Scores Through Fuzzy Logic

## Why:

[1] has a good risk index, but has the main limitations:
### Uncertainties from Critical Habitate Values
[1] mentions
> "Areas designated as ‘likely’ critical habitat (CH) were given a high biodiversity value k(CH = 1) and areas designated as ‘potential’ critical habitat were given a moderate biodiversity value (CH = 0.5) because of the uncertainty of their role as critical habitats"

**The interpretation and attribution of precise values to this imprecise linguistic variable leads to uncertainty, as it fails to account for the nuances of its values ("likely" and "potential") **

### Limitations of Mean-based Risk Index
[1] Biodiversity risk = (CH + PA + SI)/3
> "The biodiversity risk index measures risk at a relative scale. It attributes greater relative risk to locations that contain multiple sensitive ecological features than just a single ecological feature"

However, **using the mean of these three components major limitations**. In locations scenarios where only one of the components is high, the risk value is lower, but the authors note that this should not necessaryly be considered as such:
> "Although locations where only one type of ecologically sensitive feature occurs will have a lower risk value, these areas should not be interpreted as having negligible risk associated with development"

### Interpretability of Risk Index for Policymakers
It might be harder for policymakers to interpret the risk index solely from their component values and algebraic formulas.

### Migrating threathened species and NPA use case
if endangered wolfs move to another location that received investment, because now they are more suitable and better in biodiversity, then it could look like the N+A caused the bio risk in the improved location to get worse (higher risk).


## How:
Maintain the PAI, CHI, and SI components from [1] used in the Risk Index, but combine them through the use of rule-based Fuzzy Inference Systems (FIS). This would create a risk score with the same concept, but capable of better handing the uncertainties and imprecisions from real-world data, allowing for a better representation of the nuances of values in these three components.

### CHI, HFI and SRI as Linguistic Fuzzy Variables
CHI is already a linguistic variable. HFIs and SRI could be converted into similar variables.
Example: CHI would be represented by two fuzzy membership functions (MFs), representing the linguistic values of 'likely' and 'possible'. "Likely" could be represented by a triangular MF with values (0.6, 0.8, 1), while 'possible' could be represented by a triangular MF with values (0.3, 0.5, 0.7).
meanwhile then the risk score would be represented by multiple if-then-rules, such as:
> if CHI == 'likely' and PAI == 'protected' and SRI == 'High' THEN Risk == "High"

The combination of these multiple rules would both encompass the orignal "means" approach, but also take into account the fact that if only one of the components is high, then the risk should't just negieble. Example:
> if CHI == 'potential' and PAI == 'unprotected' and SRI == 'High' THEN Risk == "Medium"



### Interpretability for Policymakers
Using natural language values and if-then-rules that are closer to the policymakers context should also help with interpreting the meaning behind the proposed risk index.
Sihams SRI should go over this.

## Evaluation and Results
###  Risk score on specific region (Luxemburg?)
### Validation on past major biodiversity loss scenarios
Also would be good to "validate" the usefullness of the risk score by showing the risk score in some specific location in the past where some years later there was a major biodiversity loss due to urbanisation/climatechange (itally / spain?). This way (depending on the results) we could say something along the lines of: if authorities had access to this risk index, they would have been able to identify this high risk location 5 years before the major incident of biodiversity loss. or something like that.

### Validation by comparing interpretability of results
Compare the explanation and interpretability of the original risk score from their crisp (non-fuzzy) values, compared to the nice view where we can show which rules where activated when running the inference for a given input. i.e., with FIS you can say: the risk index is 0.3 because in this case, rules 1, 3 and 5 where used, with rule 1 being the most critical to this result. And things like that. And since each rule is just a if-then rule, this will be much easier to read then having to go back and forth from scores (0-1) and each components formulas.



### missing rules from initial rule creations
.============================================================
FAILED INPUTS - CRISP VALUES & DOMINANT MEMBERSHIP FUNCTIONS
============================================================
Input  1: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.25 (medium-low )
Input  2: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.25 (medium-low )
Input  3: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.25 (medium-low )
Input  4: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.30 (medium-low )
Input  5: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.30 (medium-low )
Input  6: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.35 (medium-low )
Input  7: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.35 (medium-low )
Input  8: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.40 (medium-low )
Input  9: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.40 (medium-low )
Input 10: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.45 (medium     )
Input 11: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.45 (medium     )
Input 12: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.50 (medium     )
Input 13: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.50 (medium     )
Input 14: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.55 (medium     )
Input 15: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.55 (medium     )
Input 16: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.60 (medium-high)
Input 17: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.60 (medium-high)
Input 18: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.65 (medium-high)
Input 19: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.65 (medium-high)
Input 20: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.70 (medium-high)
Input 21: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.70 (medium-high)
Input 22: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.75 (medium-high)
Input 23: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.75 (medium-high)
Input 24: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.75 (medium-high)
Input 25: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.80 (medium-high)
Input 26: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.80 (medium-high)
Input 27: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.80 (medium-high)
Input 28: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.85 (high       )
Input 29: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.85 (high       )
Input 30: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.85 (high       )
Input 31: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.90 (high       )
Input 32: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.90 (high       )
Input 33: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.90 (high       )
Input 34: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 0.95 (high       )
Input 35: ch= 0.5 (potential) | pa=1 (protected  ) | si= 0.95 (high       )
Input 36: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 0.95 (high       )
Input 37: ch= 0.0 (unknown  ) | pa=1 (protected  ) | si= 1.00 (high       )
Input 38: ch= 0.5 (potential) | pa=1 (protected  ) | si= 1.00 (high       )
Input 39: ch= 1.0 (likely   ) | pa=1 (protected  ) | si= 1.00 (high       )
============================================================

MISSING RULE PATTERNS (Grouped by frequency):
----------------------------------------
Pattern: ch=unknown, pa=protected, si=medium-high           | Count:  5
Pattern: ch=likely, pa=protected, si=medium-high            | Count:  5
Pattern: ch=unknown, pa=protected, si=high                  | Count:  4
Pattern: ch=potential, pa=protected, si=high                | Count:  4
Pattern: ch=likely, pa=protected, si=high                   | Count:  4
Pattern: ch=unknown, pa=protected, si=medium-low            | Count:  3
Pattern: ch=likely, pa=protected, si=medium-low             | Count:  3
Pattern: ch=unknown, pa=protected, si=medium                | Count:  3
Pattern: ch=likely, pa=protected, si=medium                 | Count:  3
Pattern: ch=potential, pa=protected, si=medium-high         | Count:  2
Pattern: ch=unknown, pa=protected, si=low                   | Count:  1
Pattern: ch=potential, pa=protected, si=low                 | Count:  1
Pattern: ch=likely, pa=protected, si=low                    | Count:  1

============================================================
SUGGESTED RULES TO ADD:
----------------------------------------
Rule 1: IF ch IS likely AND pa IS protected AND si IS high THEN risk IS ???
Rule 2: IF ch IS likely AND pa IS protected AND si IS low THEN risk IS ???
Rule 3: IF ch IS likely AND pa IS protected AND si IS medium THEN risk IS ???
Rule 4: IF ch IS likely AND pa IS protected AND si IS medium-high THEN risk IS ???
Rule 5: IF ch IS likely AND pa IS protected AND si IS medium-low THEN risk IS ???
Rule 6: IF ch IS potential AND pa IS protected AND si IS high THEN risk IS ???
Rule 7: IF ch IS potential AND pa IS protected AND si IS low THEN risk IS ???
Rule 8: IF ch IS potential AND pa IS protected AND si IS medium-high THEN risk IS ???
Rule 9: IF ch IS unknown AND pa IS protected AND si IS high THEN risk IS ???
Rule 10: IF ch IS unknown AND pa IS protected AND si IS low THEN risk IS ???
Rule 11: IF ch IS unknown AND pa IS protected AND si IS medium THEN risk IS ???
Rule 12: IF ch IS unknown AND pa IS protected AND si IS medium-high THEN risk IS ???
Rule 13: IF ch IS unknown AND pa IS protected AND si IS medium-low THEN risk IS ???



# References
[1]: Yang H, Simmons BA, Ray R, Nolte C, Gopal S, Ma Y, Ma X, Gallagher KP. Risks to global biodiversity and Indigenous lands from China’s overseas development finance. Nature Ecology & Evolution. 2021 Nov;5(11):1520-9.
