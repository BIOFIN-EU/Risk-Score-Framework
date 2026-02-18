import os, warnings, contextlib, io
from decouple import config

import ee
ee.Authenticate()
ee.Initialize(project='coral-subject-477515-k6')


# -----------------------------
# Warnings: keep output clean
# -----------------------------
warnings.filterwarnings("ignore", message=".*does not have valid feature names.*")
warnings.filterwarnings("ignore", message=".*use_label_encoder.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
_null = io.StringIO()
_silence_out = contextlib.redirect_stdout(_null)
_silence_err = contextlib.redirect_stderr(_null)

# -----------------------------
# Folders
# -----------------------------

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SOURCE_DIR)
BASE_DATA_DIR = os.path.join(PROJECT_ROOT, "data")


class SpeciesSuitabilityConfig():
    def __init__(self, **kwargs):
        self.BASE_DATA_DIR = kwargs.get('BASE_DATA_DIR', BASE_DATA_DIR)
        self.COUNTRY_CODE = kwargs.get('COUNTRY_CODE', "LU")
        self.MYDRIVE = os.path.join(self.BASE_DATA_DIR, f'country_{self.COUNTRY_CODE}')
        self.SPECIES_SCIENTIFIC_NAME = kwargs.get('SPECIES_SCIENTIFIC_NAME', "Lullula arborea")
        self.SCENARIO_MODEL = kwargs.get('SCENARIO_MODEL', "EC-Earth3-Veg")
        self.MIDDLE_SCENARIO = kwargs.get('MIDDLE_SCENARIO', "ssp245")
        self.UPPER_SCENARIO = kwargs.get('UPPER_SCENARIO', "ssp585")
        self.SCENARIOS = kwargs.get('SCENARIOS', [self.MIDDLE_SCENARIO, self.UPPER_SCENARIO])
        self.PERIODS = kwargs.get('PERIODS', ["2021-2040", "2041-2060"])
        self.EE_EXPORT_FOLDER_NAME = kwargs.get('EE_EXPORT_FOLDER_NAME', "All_Sp")
        self.GRAIN_SIZE = kwargs.get('GRAIN_SIZE', 1000)
        self.NODATA_VAL = kwargs.get('NODATA_VAL', -9999.0)
        self.AOI_BBOX = kwargs.get('AOI_BBOX', (5.737, 49.447, 6.527, 50.181))
        self.GBIF_API_BASE = kwargs.get('GBIF_API_BASE', "https://api.gbif.org/v1/occurrence/search")
        self.DEFAULT_BIN_THR = kwargs.get('DEFAULT_BIN_THR', 0.50)

        # Derived attributes
        self.SPECIES_SAFE = self.SPECIES_SCIENTIFIC_NAME.replace(" ", "_")
        self.ALL_SPECIES_ROOT = os.path.join(self.MYDRIVE, self.EE_EXPORT_FOLDER_NAME)
        self.SPECIES_DIR = os.path.join(self.ALL_SPECIES_ROOT, self.SPECIES_SAFE)
        self.DATA_DIR_NAME = f"data_{self.SPECIES_SAFE}"
        self.DATA_DIR = os.path.join(self.SPECIES_DIR, self.DATA_DIR_NAME)

        # INPUT_DIR with the logic from your script
        self.INPUT_DIR = os.path.join(self.MYDRIVE, "Input_data")

        # Future TIFs
        self.FUTURE_TIF_ROOTS = kwargs.get('FUTURE_TIF_ROOTS', [self.BASE_DATA_DIR])
        self.FUTURE_TIF_REL_TEMPLATE = kwargs.get('FUTURE_TIF_REL_TEMPLATE',
                                                  "wc2.1_30s_bioc_{model}_{ssp}_{period}.tif")

        # Current predictors paths
        self.WC_CURRENT_DRIVE = os.path.join(self.INPUT_DIR, "worldclim_bio_current.tif")
        self.ENV_1KM_DRIVE = os.path.join(self.INPUT_DIR, "elev_hs_slope_tcc_1km.tif")
        self.WC_CURRENT_INTERP = os.path.join(self.INPUT_DIR, "worldclim_bio_current_Interpolated.tif")
        self.ENV_1KM_INTERP = os.path.join(self.INPUT_DIR, "elev_hs_slope_tcc_1km_Interpolated.tif")
        self.CURRENT_STACK = os.path.join(self.INPUT_DIR, "ActualPredictorsSubset_1km_Interpolated.tif")

        # Current outputs
        self.CURRENT_PROB = os.path.join(self.DATA_DIR, "suitability_current.tif")
        self.CURRENT_BIN = os.path.join(self.DATA_DIR, "suitability_current_binary.tif")
        self.MODEL_BUNDLE_RF = os.path.join(self.DATA_DIR, "model_current.joblib")

        # Training CSV & AOI
        self.CSV_PREFIX = f"KMeans_{self.SPECIES_SAFE}"
        self.AOI_PREFIX = f"AOI_buffer_50km_{self.SPECIES_SAFE}"
        self.TRAIN_CSV = os.path.join(self.DATA_DIR, f"{self.CSV_PREFIX}.csv")

        self._ensure_dirs_exist()

    def _ensure_dirs_exist(self):
        os.makedirs(self.ALL_SPECIES_ROOT, exist_ok=True)
        os.makedirs(self.SPECIES_DIR, exist_ok=True)
        os.makedirs(self.DATA_DIR, exist_ok=True)

        os.makedirs(self.INPUT_DIR, exist_ok=True)
