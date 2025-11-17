import os

import ee

from underwriting.conf import (
    MYDRIVE,
    EE_EXPORT_FOLDER_NAME,
    GBIF_API_BASE,
    DATA_DIR,
    TRAIN_CSV,
    SPECIES_SCIENTIFIC_NAME,
    COUNTRY_CODE,
    AOI_PREFIX,
    CSV_PREFIX,
    GRAIN_SIZE,
    SPECIES_SAFE,
    CURRENT_STACK,
    MODEL_BUNDLE_RF,
    SCENARIO_MODEL,
    CURRENT_PROB,
    CURRENT_BIN,
    NODATA_VAL,
    SCENARIOS,
    PERIODS,
    FUTURE_TIF_ROOTS,
    INPUT_DIR,
    ENV_1KM_INTERP,
    SPECIES_DIR,
    DEFAULT_BIN_THR,
)

from underwriting.species_models.utils import (
    load_gbif_data,
    remove_duplicates,
    prepare_predictors,
    filter_variables_by_vif,
    generate_presence_absence_data,
    export_aoi_csv_files,
    # relocate_with_linger_and_purge,
    verify_files_exist,
    find_aoi_shapefile,
    load_aoi_or_fallback,
    export_and_interpolate_predictors,
    interpolate_files_or_skip,
    return_and_save_bands_list,
    build_stack_if_existing_current_interp,
    train_current_rf_model,
    train_multi_models,
    process_future_maps,
    clipand_interpolate_future_raster_for_all,
    predict_and_export_future_maps_for_all,
    predict_future_species_suitability,
)




def build_training_data_if_missing():
    """Main function to check and build AOI + Training CSV if missing."""
    # Check if files already exist
    need_csv = not os.path.exists(TRAIN_CSV)
    need_aoi = not os.path.exists(os.path.join(DATA_DIR, f"{AOI_PREFIX}.shp"))

    if not (need_csv or need_aoi):
        return

    # Load and process GBIF data
    ee_points = load_gbif_data(
        SPECIES_SCIENTIFIC_NAME, COUNTRY_CODE,
        exclude_year=1995,           # Exclude records from 1995
        exclude_months=(8, 9)        # Exclude August (8) to September (9)
    )
    if ee_points is None:
        return

    # Remove duplicates and create AOI
    data_fc = remove_duplicates(ee_points, GRAIN_SIZE)
    aoi_ee = data_fc.geometry().bounds().buffer(distance=50000, maxError=1000)

    # Prepare predictors and filter variables
    predictors, pvals_df = prepare_predictors(aoi_ee, GRAIN_SIZE)
    filtered_pvals_df, bands = filter_variables_by_vif(pvals_df)

    # Generate presence/absence data
    samples_table = generate_presence_absence_data(data_fc, predictors, bands, GRAIN_SIZE)


    # Export to local
    file_paths = export_aoi_csv_files(
        aoi_ee,
        samples_table,
        SPECIES_SAFE,
        DATA_DIR,
        AOI_PREFIX,
        CSV_PREFIX,
        export_to_google_drive=False  # Set to True to use Google Drive (when enabled)
    )

def print_final_outputs(data_dir, csv_prefix, aoi_prefix, species_safe, current_prob, current_bin):
    """Print final output summary."""
    print("\n🎉 DONE. Key outputs in:")
    print(" -", data_dir)
    print("   •", os.path.join(data_dir, f"{csv_prefix}.csv"))
    print("   •", os.path.join(data_dir, f"{aoi_prefix}.shp"))
    print("   •", os.path.join(data_dir, f"bands_selected_{species_safe}.csv"))
    print("   •", os.path.join(data_dir, "worldclim_bio_current_Interpolated.tif"))
    print("   •", os.path.join(data_dir, "elev_hs_slope_tcc_1km_Interpolated.tif"))
    print("   •", os.path.join(data_dir, f"model_RF_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, f"model_SVM_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, f"model_XGB_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, f"model_LGBM_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, f"model_CatBoost_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, f"model_Ensemble_{species_safe}.joblib"))
    print("   •", os.path.join(data_dir, "model_current.joblib"), "(legacy RF bundle)")
    print("   •", current_prob)
    print("   •", current_bin)



def first_step_for_each_model():
    build_training_data_if_missing()
    verify_files_exist(AOI_PREFIX, CSV_PREFIX, dst_dir=DATA_DIR)
    aoi, aoi_gdf_wgs84, aoi_bbox = load_aoi_or_fallback(DATA_DIR, SPECIES_SAFE)
    export_and_interpolate_predictors(aoi_bbox, aoi)
    interpolate_files_or_skip()
    bands = return_and_save_bands_list()
    build_stack_if_existing_current_interp(bands)
    train_current_rf_model(
        train_csv_path=TRAIN_CSV,
        current_stack_path=CURRENT_STACK,
        model_bundle_path=MODEL_BUNDLE_RF,
        data_dir=DATA_DIR,
        species_safe=SPECIES_SAFE,
        scenario_model=SCENARIO_MODEL,
        current_prob_path=CURRENT_PROB,
        current_bin_path=CURRENT_BIN,
        nodata_val=NODATA_VAL
    )

    models, best_xgb, best_lgb, best_cb, ev, train_bands_final = train_multi_models(
        train_csv_path=TRAIN_CSV,
        current_stack_path=CURRENT_STACK,
        data_dir=DATA_DIR,
        species_safe=SPECIES_SAFE,
        scenario_model=SCENARIO_MODEL
    )
    print("Trained models:", models)
    print("Best XGBoost model:", best_xgb)
    print("Best LightGBM model:", best_lgb)
    print("Best CatBoost model:", best_cb)
    print("Evaluation metrics:", ev)
    print("Final training bands:", train_bands_final)

    process_future_maps(
        scenarios=SCENARIOS,
        periods=PERIODS,
        scenario_model=SCENARIO_MODEL,
        future_tif_roots=FUTURE_TIF_ROOTS,
        aoi_gdf_wgs84=aoi_gdf_wgs84,
        input_dir=INPUT_DIR,
        env_1km_interp=ENV_1KM_INTERP,
        bands=bands,
        data_dir=DATA_DIR,
        species_safe=SPECIES_SAFE,
        species_dir=SPECIES_DIR,
        nodata_val=NODATA_VAL,
        default_bin_thr=DEFAULT_BIN_THR,
        models=models,
        best_xgb=best_xgb,
        best_lgb=best_lgb,
        best_cb=best_cb,
        ev=ev,
        train_bands_final=train_bands_final
    )

    print_final_outputs(
        data_dir=DATA_DIR,
        csv_prefix=CSV_PREFIX,
        aoi_prefix=AOI_PREFIX,
        species_safe=SPECIES_SAFE,
        current_prob=CURRENT_PROB,
        current_bin=CURRENT_BIN
    )

def second_step_for_each_model():
    clipand_interpolate_future_raster_for_all(
        data_dir=DATA_DIR,
        input_dir=INPUT_DIR,
        scenarios=SCENARIOS,
        periods=PERIODS,
        scenario_model=SCENARIO_MODEL,
        future_tif_roots=FUTURE_TIF_ROOTS,
        spec_safe=SPECIES_SAFE
    )

def third_step_for_each_model():
    predict_and_export_future_maps_for_all(
        data_dir=DATA_DIR,
        input_dir=INPUT_DIR,
        species_dir=SPECIES_DIR,
        scenario_model=SCENARIO_MODEL,
        scenarios=SCENARIOS,
        periods=PERIODS,
        species_safe=SPECIES_SAFE,
        default_bin_thr=DEFAULT_BIN_THR
    )



def simplified_predict_future_species_suitability():
    import json
    ret_json = predict_future_species_suitability(
        data_dir=DATA_DIR,
        input_dir=INPUT_DIR,
        scenarios=SCENARIOS,
        periods=PERIODS,
        species_safe=SPECIES_SAFE,
        summary_only=True
    )
    print(json.dumps(ret_json, indent=4))

def main():
    # first_step_for_each_model()
    # second_step_for_each_model()
    # third_step_for_each_model()
    simplified_predict_future_species_suitability()


if __name__ == '__main__':
    main()
