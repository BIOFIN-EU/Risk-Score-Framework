import numpy as np



class MAPriorityModel(object):
    """
    Management Action Priority Model based on Tan et al. (2024).

    Combines biodiversity risk score (0-1) and climate resilience score (0-1)
    to determine priority management actions for forest protection and restoration.

    Categories based on resilience × risk matrix:
    - 0: Low Priority (Low Resilience, any risk level)
    - 1: Active Protection I (High Resilience + High Risk)
    - 2: Active Protection II (High Resilience + Medium Risk)
    - 3: Passive Protection (High Resilience + Low Risk)
    - 4: Active Restoration I (Medium Resilience + High Risk)
    - 5: Active Restoration II (Medium Resilience + Medium Risk)
    - 6: Passive Restoration (Medium Resilience + Low Risk)
    """
    def __init__(self, risk_thresholds, resilience_thresholds):
        self.raster_nodata = -9999
        self.risk_thresholds = risk_thresholds
        self.resilience_thresholds = resilience_thresholds

    def pre_process(self, biorisk_raster, resilience_raster):
        self.biorisk_raster = biorisk_raster
        self.resilience_raster = resilience_raster
        self.valid_mask = (self.biorisk_raster >= 0) & (self.resilience_raster >= 0)



    def _classify_value(self, value, thresholds):
        """Classify a value (0-1) into low/medium/high based on thresholds."""
        if value <= thresholds['low']:
            return 'low'
        elif value <= thresholds['medium']:
            return 'medium'
        else:
            return 'high'

    def _get_priority_category(self, risk_class, resilience_class):
        """Determine priority category based on risk and resilience classes."""
        # Low resilience -> Low Priority (category 0) regardless of risk
        if resilience_class == 'low':
            return 0

        # High resilience -> Protection zones
        if resilience_class == 'high':
            if risk_class == 'high':
                return 1  # Active Protection I
            elif risk_class == 'medium':
                return 2  # Active Protection II
            else:  # low risk
                return 3  # Passive Protection

        # Medium resilience -> Restoration zones
        if resilience_class == 'medium':
            if risk_class == 'high':
                return 4  # Active Restoration I
            elif risk_class == 'medium':
                return 5  # Active Restoration II
            else:  # low risk
                return 6  # Passive Restoration


    def post_processing(self, priority_raster):
        pass

    def get_category_info(self):
        """Return metadata about each priority category."""
        return {
            0: {
                "label": "Low Priority - Deferred Action",
                "label_short": "Low Priority",
                "description": "Low resilience areas where conservation resources should be allocated last, but deserve restoration when resources are abundant, especially in key locations for species migration.",
                "color": "#374151"
            },
            1: {
                "label": "Active Protection Zones I (AP I)",
                "label_short": "AP I",
                "description": "Region with high resilience and high risk. Highest priority for active protection due to elevated risk levels.",
                "color": "#135d18"
            },
            2: {
                "label": "Active Protection Zones II (AP II)",
                "label_short": "AP II",
                "description": "Region with high resilience and medium risk. Active protection with proactive management measures.",
                "color": "#0cc02a"
            },
            3: {
                "label": "Passive Protection Zones (PP)",
                "label_short": "PP",
                "description": "Region with high resilience and low risk. Minimal intervention required.",
                "color": "#86efac"
            },
            4: {
                "label": "Active Restoration Zones I (AR I)",
                "label_short": "AR I",
                "description": "Region with medium resilience and high risk. Prioritizes assisted and reconstructive restoration.",
                "color": "#eab308"
            },
            5: {
                "label": "Active Restoration Zones II (AR II)",
                "label_short": "AR II",
                "description": "Region with medium resilience and medium risk. Restoration measures to overcome specific obstacles.",
                "color": "#f97316"
            },
            6: {
                "label": "Passive Restoration Zones (PR)",
                "label_short": "PR",
                "description": "Region with medium resilience and low risk. Natural restoration strategies.",
                "color": "#dc2626"
            }
        }


    def run(self, biorisk_raster, resilience_raster):
        self.pre_process(biorisk_raster, resilience_raster)

        # Create empty priority raster with same shape
        priority_raster = np.full_like(self.biorisk_raster, self.raster_nodata, dtype=np.int16)

        # Extract valid pixels
        risk_valid = self.biorisk_raster[self.valid_mask]
        resilience_valid = self.resilience_raster[self.valid_mask]

        # Classify each valid pixel
        categories = []
        for risk_val, resilience_val in zip(risk_valid, resilience_valid):
            risk_class = self._classify_value(risk_val, self.risk_thresholds)
            resilience_class = self._classify_value(resilience_val, self.resilience_thresholds)
            category = self._get_priority_category(risk_class, resilience_class)
            categories.append(category)

        # Assign categories to raster
        priority_raster[self.valid_mask] = categories

        return priority_raster

