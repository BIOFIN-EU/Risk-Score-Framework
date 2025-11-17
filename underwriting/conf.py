import os, warnings, contextlib, io
from decouple import config

import ee
ee.Authenticate()
ee.Initialize(project='coral-subject-477515-k6')

# -----------------------------
# CONFIG (edit these two)
# -----------------------------
SPECIES_SCIENTIFIC_NAME = "Lullula arborea"  # e.g., "Oenanthe oenanthe"
COUNTRY_CODE            = "LU"                  # GBIF country filter

# GCM & scenarios
SCENARIO_MODEL = "EC-Earth3-Veg"
MIDDLE_SCENARIO = "ssp245"
UPPER_SCENARIO = "ssp585"
SCENARIOS      = [MIDDLE_SCENARIO, UPPER_SCENARIO]
PERIODS        = ["2021-2040", "2041-2060"]



# -----------------------------
# Folders
# -----------------------------

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SOURCE_DIR)

MYDRIVE          = os.path.join(PROJECT_ROOT, "data")
# Where EE images will be exported (flat folder name only)
EE_EXPORT_FOLDER_NAME = "All_Sp"
ALL_SPECIES_ROOT = os.path.join(MYDRIVE, EE_EXPORT_FOLDER_NAME)
SPECIES_SAFE     = SPECIES_SCIENTIFIC_NAME.replace(" ", "_")
SPECIES_DIR      = os.path.join(ALL_SPECIES_ROOT, SPECIES_SAFE)
DATA_DIR_NAME    = f"data_{SPECIES_SAFE}"
DATA_DIR         = os.path.join(SPECIES_DIR, DATA_DIR_NAME)

# If some future TIFs live on another Drive, add its mount root here
FUTURE_TIF_ROOTS = [
    MYDRIVE,
]
FUTURE_TIF_REL_TEMPLATE = "wc2.1_30s_bioc_{model}_{ssp}_{period}.tif"


os.makedirs(ALL_SPECIES_ROOT, exist_ok=True)
os.makedirs(SPECIES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# Input_data (working rasters)
INPUT_DIR = os.path.join(MYDRIVE, "Input_data")
os.makedirs(INPUT_DIR, exist_ok=True)

GBIF_API_BASE = "https://api.gbif.org/v1/occurrence/search"
# -----------------------------
# Constants
# -----------------------------
NODATA_VAL = -9999.0
AOI_BBOX   = (5.737, 49.447, 6.527, 50.181)   # fallback bbox
GRAIN_SIZE = 1000

# Current predictors (download & interpolate)
WC_CURRENT_DRIVE  = os.path.join(INPUT_DIR, "worldclim_bio_current.tif")
ENV_1KM_DRIVE     = os.path.join(INPUT_DIR, "elev_hs_slope_tcc_1km.tif")
WC_CURRENT_INTERP = os.path.join(INPUT_DIR, "worldclim_bio_current_Interpolated.tif")
ENV_1KM_INTERP    = os.path.join(INPUT_DIR, "elev_hs_slope_tcc_1km_Interpolated.tif")
CURRENT_STACK     = os.path.join(INPUT_DIR, "ActualPredictorsSubset_1km_Interpolated.tif")

# Current outputs (store in data_<species>)
CURRENT_PROB     = os.path.join(DATA_DIR, "suitability_current.tif")
CURRENT_BIN      = os.path.join(DATA_DIR, "suitability_current_binary.tif")
MODEL_BUNDLE_RF  = os.path.join(DATA_DIR, "model_current.joblib")  # legacy RF bundle name
DEFAULT_BIN_THR  = 0.50

# Training CSV & AOI shapefile
CSV_PREFIX = f"KMeans_{SPECIES_SAFE}"
AOI_PREFIX = f"AOI_buffer_50km_{SPECIES_SAFE}"
TRAIN_CSV  = os.path.join(DATA_DIR, f"{CSV_PREFIX}.csv")


# -----------------------------
# Warnings: keep output clean
# -----------------------------
warnings.filterwarnings("ignore", message=".*does not have valid feature names.*")
warnings.filterwarnings("ignore", message=".*use_label_encoder.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
_null = io.StringIO()
_silence_out = contextlib.redirect_stdout(_null)
_silence_err = contextlib.redirect_stderr(_null)
