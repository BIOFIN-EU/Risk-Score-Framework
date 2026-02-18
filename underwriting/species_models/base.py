import os


from underwriting.conf import (
    SpeciesSuitabilityConfig
)

from underwriting.species_models.utils import (
    SpeciesSuitabilityUtils
)


class SpeciesSuitabilityModel():
    def __init__(self, new_configs):
        self.setup_configs(new_configs)

    def setup_configs(self, new_configs):
        self.config = SpeciesSuitabilityConfig(**new_configs)
        self.ssi_utils = SpeciesSuitabilityUtils(self.config)


    def build_training_data_if_missing(self):
        """Main function to check and build AOI + Training CSV if missing."""
        # Check if files already exist
        need_csv = not os.path.exists(self.config.TRAIN_CSV)
        need_aoi = not os.path.exists(os.path.join(self.config.DATA_DIR, f"{self.config.AOI_PREFIX}.shp"))

        if not (need_csv or need_aoi):
            return

        # Load and process GBIF data
        ee_points = self.ssi_utils.load_gbif_data(
            self.config.SPECIES_SCIENTIFIC_NAME, self.config.COUNTRY_CODE,
            exclude_year=1995,           # Exclude records from 1995
            exclude_months=(8, 9)        # Exclude August (8) to September (9)
        )
        if ee_points is None:
            return

        # Remove duplicates and create AOI
        data_fc = self.ssi_utils.remove_duplicates(ee_points, self.config.GRAIN_SIZE)
        aoi_ee = data_fc.geometry().bounds().buffer(distance=50000, maxError=1000)

        # Prepare predictors and filter variables
        predictors, pvals_df = self.ssi_utils.prepare_predictors(aoi_ee, self.config.GRAIN_SIZE)
        filtered_pvals_df, bands = self.ssi_utils.filter_variables_by_vif(pvals_df)

        # Generate presence/absence data
        samples_table = self.ssi_utils.generate_presence_absence_data(data_fc, predictors, bands, self.config.GRAIN_SIZE)


        # Export to local
        file_paths = self.ssi_utils.export_aoi_csv_files(
            aoi_ee,
            samples_table,
            self.config.SPECIES_SAFE,
            self.config.DATA_DIR,
            self.config.AOI_PREFIX,
            self.config.CSV_PREFIX,
            export_to_google_drive=False  # Set to True to use Google Drive (when enabled)
        )

    def print_final_outputs(self, data_dir, csv_prefix, aoi_prefix, species_safe, current_prob, current_bin):
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



    def first_step_for_each_model(self):
        print("First step")
        self.build_training_data_if_missing()
        self.ssi_utils.verify_files_exist(self.config.AOI_PREFIX, self.config.CSV_PREFIX, dst_dir=self.config.DATA_DIR)
        aoi, aoi_gdf_wgs84, aoi_bbox = self.ssi_utils.load_aoi_or_fallback(self.config.DATA_DIR, self.config.SPECIES_SAFE)
        self.ssi_utils.export_and_interpolate_predictors(aoi_bbox, aoi)
        self.ssi_utils.interpolate_files_or_skip()
        bands = self.ssi_utils.return_and_save_bands_list()
        self.ssi_utils.build_stack_if_existing_current_interp(bands)
        self.ssi_utils.train_current_rf_model(
            train_csv_path=self.config.TRAIN_CSV,
            current_stack_path=self.config.CURRENT_STACK,
            model_bundle_path=self.config.MODEL_BUNDLE_RF,
            data_dir=self.config.DATA_DIR,
            species_safe=self.config.SPECIES_SAFE,
            scenario_model=self.config.SCENARIO_MODEL,
            current_prob_path=self.config.CURRENT_PROB,
            current_bin_path=self.config.CURRENT_BIN,
            nodata_val=self.config.NODATA_VAL
        )

        models, best_xgb, best_lgb, best_cb, ev, train_bands_final = self.ssi_utils.train_multi_models(
            train_csv_path=self.config.TRAIN_CSV,
            current_stack_path=self.config.CURRENT_STACK,
            data_dir=self.config.DATA_DIR,
            species_safe=self.config.SPECIES_SAFE,
            scenario_model=self.config.SCENARIO_MODEL
        )
        print("Trained models:", models)
        print("Best XGBoost model:", best_xgb)
        print("Best LightGBM model:", best_lgb)
        print("Best CatBoost model:", best_cb)
        print("Evaluation metrics:", ev)
        print("Final training bands:", train_bands_final)

        self.ssi_utils.process_future_maps(
            scenarios=self.config.SCENARIOS,
            periods=self.config.PERIODS,
            scenario_model=self.config.SCENARIO_MODEL,
            future_tif_roots=self.config.FUTURE_TIF_ROOTS,
            aoi_gdf_wgs84=aoi_gdf_wgs84,
            input_dir=self.config.INPUT_DIR,
            env_1km_interp=self.config.ENV_1KM_INTERP,
            bands=bands,
            data_dir=self.config.DATA_DIR,
            species_safe=self.config.SPECIES_SAFE,
            species_dir=self.config.SPECIES_DIR,
            nodata_val=self.config.NODATA_VAL,
            default_bin_thr=self.config.DEFAULT_BIN_THR,
            models=models,
            best_xgb=best_xgb,
            best_lgb=best_lgb,
            best_cb=best_cb,
            ev=ev,
            train_bands_final=train_bands_final
        )

        self.print_final_outputs(
            data_dir=self.config.DATA_DIR,
            csv_prefix=self.config.CSV_PREFIX,
            aoi_prefix=self.config.AOI_PREFIX,
            species_safe=self.config.SPECIES_SAFE,
            current_prob=self.config.CURRENT_PROB,
            current_bin=self.config.CURRENT_BIN
        )

    def second_step_for_each_model(self):
        print("second_step_for_each_model")

        self.ssi_utils.clipand_interpolate_future_raster_for_all(
            data_dir=self.config.DATA_DIR,
            input_dir=self.config.INPUT_DIR,
            scenarios=self.config.SCENARIOS,
            periods=self.config.PERIODS,
            scenario_model=self.config.SCENARIO_MODEL,
            future_tif_roots=self.config.FUTURE_TIF_ROOTS,
            spec_safe=self.config.SPECIES_SAFE
        )

    def third_step_for_each_model(self):
        print("third_step_for_each_model")

        self.ssi_utils.predict_and_export_future_maps_for_all(
            data_dir=self.config.DATA_DIR,
            input_dir=self.config.INPUT_DIR,
            species_dir=self.config.SPECIES_DIR,
            scenario_model=self.config.SCENARIO_MODEL,
            scenarios=self.config.SCENARIOS,
            periods=self.config.PERIODS,
            species_safe=self.config.SPECIES_SAFE,
            default_bin_thr=self.config.DEFAULT_BIN_THR
        )



    def simplified_predict_future_species_suitability(self):
        print("simplified_predict_future_species_suitability")

        # import json
        ret_json = self.ssi_utils.predict_future_species_suitability(
            data_dir=self.config.DATA_DIR,
            input_dir=self.config.INPUT_DIR,
            scenarios=self.config.SCENARIOS,
            periods=self.config.PERIODS,
            species_safe=self.config.SPECIES_SAFE,
            summary_only=False
        )
        # import ipdb; ipdb.set_trace()
        # print(json.dumps(ret_json, indent=4))

    def run(self, new_configs=None):

        if new_configs is not None:
            self.setup_configs(new_configs)
        if not self.ssi_utils._has_models_ready(self.config.DATA_DIR, self.config.SPECIES_SAFE):
            self.first_step_for_each_model()
            self.second_step_for_each_model()
            self.third_step_for_each_model()
        self.simplified_predict_future_species_suitability()



if __name__ == '__main__':
    ssi_model = SpeciesSuitabilityModel({

    })
    # ssi_model.run({'SPECIES_SCIENTIFIC_NAME': 'Streptopelia turtur'})
    ssi_model.run()
