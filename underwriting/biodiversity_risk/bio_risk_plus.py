
class BioRiskPlusFIS(object):
    """
    Fuzzifying Urbanisation and Climate Change Risks to Biodiversity in Europe
    Original Biodiversity Risk Components:
        * CH: Critical Habitat: 0???;0.5;1
        * PA: Protected Area: 0;1
        * SI: Threatened Species Reachness:
            * HFI: Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
    Proposed Biodiversity Risk Components:
        * CH: Critical Habitat: (0: Unknown, 1: Potential, 10: Likelly)
        * PA: Protected Area: 0-1 ??? Possibily make it % of area inside protected area?
        * (Inverted ^-1) SSI: Species Suitability Index*?:
            * UCC-SRI: Urbanisation and Climate Change Influenced Species Reachness Index: 0-1
                * Species Habitat Suitability affected project urbanisation and climate change models (ssp245, ssp585).
            * HFI: Current Humam Footprint Index: 0-1; norm. mapping (0-50->0-1, with 4 -> 0.5)
                - Alternativelly, represent this with mfs and rules to cover both cases where prestine wilderness is treated one way but also accomodate to non-prestine
    FIS:
     - Antecedents: CH, PA, SSI
     - Consequents: (Biodiversity)Risk
     - Rules:
        IF CH is Unknown AND PA is Unprotected AND SI is High THEN RISK is Low
    """
    def __init__(self, *arg, **kwargs):
        self.ch_raster = []
        self.pa_raster = []
        self.ssi_raster = []
