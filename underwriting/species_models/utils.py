import os,  glob, time, shutil, zipfile, re, json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.mask import mask
from scipy.interpolate import griddata
from scipy import ndimage

from sklearn.model_selection import StratifiedKFold, RandomizedSearchCV, train_test_split
from sklearn.metrics import roc_auc_score, roc_curve, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier


from imblearn.over_sampling import SMOTE

from shapely.geometry import mapping, box
from statsmodels.stats.outliers_influence import variance_inflation_factor
import ee, geemap

from joblib import dump, load


import requests


from underwriting.conf import (
    _silence_out,
    _silence_err,
)
from underwriting.conf import ee




class SpeciesSuitabilityUtils():
    def __init__(self, base_configs):
        self.config = base_configs

    def get_gbif_species_data(self, species_name, country_code):
        params = {"scientificName":species_name,"country":country_code,
                "hasCoordinate":"true","basisOfRecord":"HUMAN_OBSERVATION","limit":10000}
        try:
            r = requests.get(self.config.GBIF_API_BASE, params=params); r.raise_for_status()
            data = r.json().get("results", [])
            return pd.json_normalize(data) if data else pd.DataFrame()
        except requests.RequestException as e:
            print(f"Request failed: {e}"); return pd.DataFrame()


    def remove_duplicates(self, fc, grain):
        rnd = ee.Image.random().reproject("EPSG:4326", None, grain)
        return rnd.sampleRegions(ee.FeatureCollection(fc), geometries=True).distinct("random")


    def load_gbif_data(self, species_name, country_code, exclude_year=None, exclude_months=None):
        """Load GBIF data for given species and country with optional filters.

        Args:
            species_name: Scientific name of the species
            country_code: ISO country code for GBIF query
            exclude_year: Year to exclude (e.g., 1995). If None, no year filtering.
            exclude_months: Tuple of (start_month, end_month) to exclude (inclusive).
                        If None, no month filtering.
        """
        df_gbif = self.get_gbif_species_data(species_name, country_code)
        if df_gbif.empty:
            print("⚠️ GBIF returned no records; continuing (expect training CSV missing).")
            return None

        gdf = gpd.GeoDataFrame(
            df_gbif,
            geometry=gpd.points_from_xy(df_gbif.decimalLongitude, df_gbif.decimalLatitude),
            crs="EPSG:4326"
        )[["species", "year", "month", "geometry"]]

        # Apply filters
        filtered_gdf = gdf.copy()

        # Filter out specific year if provided
        if exclude_year is not None:
            filtered_gdf = filtered_gdf[~filtered_gdf["year"].eq(exclude_year)]

        # Filter out month range if provided
        if exclude_months is not None:
            start_month, end_month = exclude_months
            filtered_gdf = filtered_gdf[~filtered_gdf["month"].between(start_month, end_month)]

        return geemap.geopandas_to_ee(filtered_gdf)

    def prepare_predictors(self, aoi_ee, grain_size):
        """Prepare predictor variables and sample for correlation analysis."""
        # Load environmental data
        bio = ee.Image("WORLDCLIM/V1/BIO")
        terrain = ee.Algorithms.Terrain(ee.Image("USGS/SRTMGL1_003"))
        tcc = ee.ImageCollection("NASA/MEASURES/GFCC/TC/v3").filterDate("2000-01-01", "2015-12-31")
        median_tcc = tcc.select(["tree_canopy_cover"], ["TCC"]).median()

        # Combine predictors and mask/clip
        predictors = bio.addBands(terrain).addBands(median_tcc)
        predictors = predictors.updateMask(terrain.select('elevation').gt(0)).clip(aoi_ee)

        # Sample for VIF/correlation analysis
        data_cor = predictors.sample(scale=grain_size, numPixels=5000, geometries=True)
        pvals = predictors.sampleRegions(collection=data_cor, scale=grain_size)
        pvals_df = geemap.ee_to_df(pvals)

        return predictors, pvals_df


    def filter_variables_by_vif(self, df_, threshold=10):
        """Filter variables using Variance Inflation Factor analysis."""
        remain = list(pd.DataFrame(df_).select_dtypes(include=[np.number]).columns)

        while True:
            if len(remain) <= 1:
                break

            X = df_[remain].values
            vifs = [variance_inflation_factor(X, i) for i in range(len(remain))]
            mx, idx = max(vifs), vifs.index(max(vifs))

            if mx < threshold:
                break

            print(f"Removing '{remain[idx]}' with VIF {mx:.2f}")
            del remain[idx]

        return df_[remain], remain

    def generate_presence_absence_data(self, data_fc, predictors, bands, grain_size):
        """Generate presence/absence sampling data."""
        # Create presence points
        presence = data_fc.map(lambda f: f.set('PresAbs', 1))

        # Create presence mask
        presence_mask = data_fc.reduceToImage(['random'], ee.Reducer.first())\
                            .reproject('EPSG:4326', None, grain_size).mask().neq(1).selfMask()

        # Cluster analysis for absence sampling
        cl_for_k = predictors.sampleRegions(
            collection=data_fc.randomColumn().sort('random').limit(100),
            properties=[], scale=grain_size
        )
        clusterer = ee.Clusterer.wekaKMeans(nClusters=2, distanceFunction="Euclidean").train(cl_for_k)
        cl_result = predictors.cluster(clusterer)
        cl_id = cl_result.sampleRegions(
            collection=data_fc.randomColumn().sort('random').limit(200),
            properties=[], scale=grain_size
        )
        cl_id = ee.FeatureCollection(cl_id).reduceColumns(ee.Reducer.mode(), ['cluster'])
        cl_id = ee.Number(cl_id.get('mode')).subtract(1).abs()
        cl_mask = cl_result.select(['cluster']).eq(cl_id)

        # Create area for pseudo-absence sampling
        area_for_pa = presence_mask.updateMask(cl_mask).clip(data_fc.geometry().bounds().buffer(distance=50000, maxError=1000))

        # Sample absence points
        absence = area_for_pa.sample(
            region=data_fc.geometry().bounds().buffer(distance=50000, maxError=1000),
            scale=grain_size,
            numPixels=data_fc.size(),
            seed=0,
            geometries=True
        ).map(lambda f: f.set('PresAbs', 0))

        # Combine presence and absence
        samples = presence.merge(absence)

        # Extract predictor values for samples
        samples_table = predictors.select(bands).toFloat()\
                                .sampleRegions(
                                    collection=samples,
                                    properties=['PresAbs'],
                                    scale=grain_size,
                                    geometries=True
                                )

        return samples_table

    def export_to_drive(self, aoi_ee, samples_table, species_safe, ee_export_folder, aoi_prefix, csv_prefix):
        """Export AOI shapefile and samples CSV to Google Drive."""
        # Export AOI
        task_aoi = ee.batch.Export.table.toDrive(
            collection=ee.FeatureCollection(aoi_ee),
            description=f'AOI_shapefile_{species_safe}',
            folder=ee_export_folder,
            fileNamePrefix=aoi_prefix,
            fileFormat='SHP'
        )
        task_aoi.start()

        # Export CSV
        task_csv = ee.batch.Export.table.toDrive(
            collection=samples_table,
            description=csv_prefix,
            folder=ee_export_folder,
            fileNamePrefix=csv_prefix,
            fileFormat='CSV'
        )
        task_csv.start()

        return [task_aoi, task_csv]

    def export_to_local(self, aoi_ee, samples_table, species_safe, data_dir, aoi_prefix, csv_prefix):
        """Export AOI shapefile and samples CSV to local directory."""
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)

        # Export AOI shapefile
        aoi_gdf = geemap.ee_to_gdf(ee.FeatureCollection(aoi_ee))
        aoi_path = os.path.join(data_dir, f"{aoi_prefix}.shp")
        aoi_gdf.to_file(aoi_path)
        print(f"✅ AOI shapefile saved to: {aoi_path}")

        # Export CSV
        samples_df = geemap.ee_to_df(samples_table)
        csv_path = os.path.join(data_dir, f"{csv_prefix}.csv")
        samples_df.to_csv(csv_path, index=False)
        print(f"✅ Training CSV saved to: {csv_path}")

        return [aoi_path, csv_path]


    def export_aoi_csv_files(self, aoi_ee, samples_table, species_safe, data_dir, aoi_prefix, csv_prefix, export_to_google_drive=False):
        """Export AOI shapefile and samples CSV to either local directory or Google Drive."""

        if export_to_google_drive:
            return self.export_to_drive(
                aoi_ee, samples_table, species_safe,
                self.config.EE_EXPORT_FOLDER_NAME, aoi_prefix, csv_prefix
            )
        else:
            # Local export
            res = self.export_to_local(aoi_ee, samples_table, species_safe, data_dir, aoi_prefix, csv_prefix)

            print("✅ Export completed successfully!")
            return res

    def verify_files_exist(self, aoi_prefix, csv_prefix, dst_dir):
        """Simple verification that required files exist in the destination directory."""
        os.makedirs(dst_dir, exist_ok=True)

        # Check for CSV file
        csv_path = os.path.join(dst_dir, f"{csv_prefix}.csv")
        csv_exists = os.path.exists(csv_path)

        # Check for required shapefile components
        required_exts = (".shp", ".shx", ".dbf", ".prj")
        aoi_files_exist = all(
            os.path.exists(os.path.join(dst_dir, f"{aoi_prefix}{ext}"))
            for ext in required_exts
        )

        if csv_exists and aoi_files_exist:
            print(f"✅ All required files are present in {dst_dir}")
            return True
        else:
            missing = []
            if not csv_exists:
                missing.append(f"{csv_prefix}.csv")
            if not aoi_files_exist:
                missing.append(f"{aoi_prefix} shapefile components")
            print(f"❌ Missing files: {', '.join(missing)}")
            return False

    # Pick up AOI shapefile path in DATA_DIR (required for all next steps)
    def find_aoi_shapefile(self, data_dir, spec_safe):
        priority = [os.path.join(data_dir, f"AOI_buffer_50km_{spec_safe}.shp"),
                    os.path.join(data_dir, f"AOI_{spec_safe}.shp")]
        for p in priority:
            if os.path.exists(p):
                return p
        cand = glob.glob(os.path.join(data_dir, "AOI_*.shp")) or glob.glob(os.path.join(data_dir, "*.shp"))
        return cand[0] if cand else None


    def load_aoi_or_fallback(self, data_dir, spec_safe):
        aoi_shp = self.find_aoi_shapefile(data_dir, spec_safe)
        aoi = None
        if aoi_shp:
            aoi_gdf_wgs84 = gpd.read_file(aoi_shp)
            if aoi_gdf_wgs84.crs is None:
                aoi_gdf_wgs84.set_crs("EPSG:4326", inplace=True)
            else:
                aoi_gdf_wgs84 = aoi_gdf_wgs84.to_crs("EPSG:4326")
            geom_series = aoi_gdf_wgs84.geometry
            aoi_geom = geom_series.union_all() if hasattr(geom_series, "union_all") else geom_series.unary_union
            aoi_geojson = mapping(aoi_geom)
            try:
                aoi = ee.Geometry(aoi_geojson)
            except Exception:
                aoi = None
            print(f"🔷 Using AOI from shapefile: {aoi_shp}")
        else:
            minx, miny, maxx, maxy = self.config.AOI_BBOX
            aoi = ee.Geometry.BBox(minx, miny, maxx, maxy)
            aoi_geom = box(*self.config.AOI_BBOX)
            aoi_gdf_wgs84 = gpd.GeoDataFrame({'geometry':[aoi_geom]}, crs="EPSG:4326")
            print("⚠️ AOI shapefile not found; using bbox fallback.")

        return aoi, aoi_gdf_wgs84, self.config.AOI_BBOX


    def export_and_interpolate_predictors(self, aoi_bbox, aoi=None):
        """Export current predictors from EE and interpolate them locally."""
        # ============================================================
        # B) CURRENT PREDICTORS: export & interpolate (and copy into data_<species>)
        # ============================================================
        try:
            band_names = [f"bio{str(i).zfill(2)}" for i in range(1, 20)]
            bio = ee.Image('WORLDCLIM/V1/BIO').select(band_names).toFloat().reproject(crs='EPSG:4326', scale=self.config.GRAIN_SIZE)

            filename = os.path.join(self.config.INPUT_DIR, "worldclim_bio_current.tif")

            bio_clipped = bio.clip(aoi if aoi is not None else ee.Geometry.Rectangle(aoi_bbox))
            geemap.ee_export_image(bio_clipped, filename=filename, scale=self.config.GRAIN_SIZE, region=aoi if aoi is not None else ee.Geometry.Rectangle(aoi_bbox))

            print("✅ Local export: worldclim_bio_current.tif")
        except Exception as e:
            print("⚠️ Skipped WC export:", e)


        try:
            srtm = ee.Image('USGS/SRTMGL1_003').select('elevation')
            elevation = srtm.reproject(crs='EPSG:4326', scale=self.config.GRAIN_SIZE).toFloat().rename('elevation')
            hillshade = ee.Terrain.hillshade(srtm).reproject(crs='EPSG:4326', scale=self.config.GRAIN_SIZE).toFloat().rename('hillshade')
            slope     = ee.Terrain.slope(srtm).reproject(crs='EPSG:4326', scale=self.config.GRAIN_SIZE).toFloat().rename('slope')
            tcc = (ee.ImageCollection('NASA/MEASURES/GFCC/TC/v3')
                    .filterDate('2000-01-01', '2015-12-31')
                    .select('tree_canopy_cover').median()
                    .reproject(crs='EPSG:4326', scale=self.config.GRAIN_SIZE).toFloat().rename('TCC'))
            env = elevation.addBands([hillshade, slope, tcc])

            filename = os.path.join(self.config.INPUT_DIR, "elev_hs_slope_tcc_1km.tif")
            # Convert EE image to local GeoTIFF
            env_clipped = env.clip(aoi if aoi is not None else ee.Geometry.Rectangle(aoi_bbox))
            geemap.ee_export_image(env_clipped, filename=filename, scale=self.config.GRAIN_SIZE, region=aoi if aoi is not None else ee.Geometry.Rectangle(aoi_bbox))

            print("✅ Local export: elev_hs_slope_tcc_1km.tif")
        except Exception as e:
            print("⚠️ Skipped ENV export:", e)


    def interpolate_raster_nearest(self, in_tif, out_tif):
        with rio.open(in_tif) as src:
            meta = src.meta.copy()
            out = []
            for b in range(1, src.count + 1):
                band = src.read(b).astype('float32')
                nd = src.nodata
                mask_ = np.isnan(band) if nd is None or (isinstance(nd, float) and np.isnan(nd)) else (band == nd)
                if mask_.any():
                    y, x = np.indices(band.shape)
                    pts = np.column_stack((x[~mask_], y[~mask_]))
                    vals = band[~mask_]
                    filled = band.copy()
                    filled[mask_] = griddata(pts, vals, (x[mask_], y[mask_]), method='nearest')
                    out.append(filled.astype('float32'))
                else:
                    out.append(band)
            meta.update(dtype='float32', nodata=None)
            with rio.open(out_tif, 'w', **meta) as dst:
                for i, arr in enumerate(out, 1):
                    dst.write(arr, i)


    def interpolate_raster_nearest_fast(self, in_tif, out_tif):
        with rio.open(in_tif) as src:
            meta = src.meta.copy()
            nd = src.nodata
            out = []
            for b in range(1, src.count + 1):
                data = src.read(b).astype('float32')
                mask_ = np.isnan(data) if nd is None or (isinstance(nd, float) and np.isnan(nd)) else (data == nd)
                if mask_.any():
                    idx = ndimage.distance_transform_edt(mask_, return_distances=False, return_indices=True)
                    data[mask_] = data[tuple(idx)][mask_]
                out.append(data)
            with rio.open(out_tif, 'w', **meta) as dst:
                for i, arr in enumerate(out, 1):
                    dst.write(arr, i)

    def interpolate_files_or_skip(self):
        # Interpolate when files appear (skip if already there)
        if os.path.exists(self.config.WC_CURRENT_DRIVE) and not os.path.exists(self.config.WC_CURRENT_INTERP):
            self.interpolate_raster_nearest(self.config.WC_CURRENT_DRIVE, self.config.WC_CURRENT_INTERP)
            print("✅ Interpolated:", self.config.WC_CURRENT_INTERP)
        elif os.path.exists(self.config.WC_CURRENT_INTERP):
            print("ℹ️ Using existing:", self.config.WC_CURRENT_INTERP)

        if os.path.exists(self.config.ENV_1KM_DRIVE) and not os.path.exists(self.config.ENV_1KM_INTERP):
            self.interpolate_raster_nearest(self.config.ENV_1KM_DRIVE, self.config.ENV_1KM_INTERP)
            print("✅ Interpolated:", self.config.ENV_1KM_INTERP)
        elif os.path.exists(self.config.ENV_1KM_INTERP):
            print("ℹ️ Using existing:", self.config.ENV_1KM_INTERP)

        # Mirror interpolated CURRENT rasters into data_<species>
        for _src in [self.config.WC_CURRENT_INTERP, self.config.ENV_1KM_INTERP]:
            if _src and os.path.exists(_src):
                _dst = os.path.join(self.config.DATA_DIR, os.path.basename(_src))
                if os.path.abspath(_src) != os.path.abspath(_dst):
                    shutil.copy2(_src, _dst)
                    print("📥 Copied to data_{}: {}".format(self.config.SPECIES_SAFE, _dst))



    # ============================================================
    # C) BANDS auto-detection + CURRENT stack
    # ============================================================
    def detect_bands_from_csv(self, csv_path):
        if not os.path.exists(csv_path):
            return None
        df_head = pd.read_csv(csv_path, nrows=200)
        cand = [c for c in df_head.columns if c != 'PresAbs']
        num = df_head[cand].select_dtypes(include=[np.number]).columns.tolist()
        keep = []
        for c in num:
            cl = c.lower()
            if re.match(r'^bio\d{2}$', cl): keep.append(c); continue
            if cl in {'elevation','slope','aspect','hillshade','tcc'}: keep.append(c); continue
        return keep


    def return_and_save_bands_list(self):
        bands = self.detect_bands_from_csv(self.config.TRAIN_CSV)
        if not bands:
            bands = ['TCC', 'aspect', 'bio08', 'bio11', 'elevation', 'slope']
            print("⚠️ CSV not found or no numeric columns; using fallback BANDS:", bands)
        else:
            print("🔎 Auto-selected BANDS from CSV:", bands)

        # Save BANDS list into data_<species>
        bands_csv_path = os.path.join(self.config.DATA_DIR, f"bands_selected_{self.config.SPECIES_SAFE}.csv")
        pd.DataFrame({"band": bands}).to_csv(bands_csv_path, index=False)
        print("📝 Saved BANDS list:", bands_csv_path)
        return bands



    def compute_aspect_from_elev(self, elevation, transform):
        dx = transform.a
        dy = -transform.e
        dz_dy, dz_dx = np.gradient(elevation, dy, dx)
        return np.mod(90.0 - np.degrees(np.arctan2(dz_dy, -dz_dx)), 360.0).astype('float32')

    def soft_fill(self, arr, nodata=None):
        if nodata is None:
            nodata = self.config.NODATA_VAL
        if np.any(arr == nodata):
            arr = arr.copy()
            arr[arr == nodata] = np.nan
            arr[np.isnan(arr)] = np.nanmean(arr)
        return arr

    def read_env_band(self, src_env, name, H, W):
        name_l = name.lower()
        idx = {'elevation':1,'hillshade':2,'slope':3,'tcc':4}.get(name_l, None)
        if idx is None: return None
        return src_env.read(idx, out_shape=(H, W), resampling=Resampling.bilinear, masked=True).filled(self.config.NODATA_VAL).astype('float32')

    def read_clim_band(self, src_clim, name):
        m = re.match(r'(?i)^bio(\d{2})$', name)
        if not m: return None
        idx = int(m.group(1))
        return src_clim.read(idx, masked=True).filled(self.config.NODATA_VAL).astype('float32')

    def build_stack_dynamic(self, band_list, out_path, clim_path, env_path):
        if not (os.path.exists(clim_path) and os.path.exists(env_path)):
            return False
        with rio.open(clim_path) as src_clim:
            clim_meta = src_clim.meta.copy()
            H, W = src_clim.height, src_clim.width
            transform = src_clim.transform

        env_cache = {}
        with rio.open(env_path) as src_env:
            if any(b.lower() == 'aspect' for b in band_list):
                elev = self.read_env_band(src_env, 'elevation', H, W)
                env_cache['elevation'] = elev
                env_cache['aspect'] = self.compute_aspect_from_elev(elev, transform)
            for b in band_list:
                bl = b.lower()
                if bl in {'elevation','slope','hillshade','tcc'} and bl not in env_cache:
                    env_cache[bl] = self.read_env_band(src_env, bl, H, W)
        clim_cache = {}
        with rio.open(clim_path) as src_clim:
            for b in band_list:
                if re.match(r'(?i)^bio\d{2}$', b) and b not in clim_cache:
                    clim_cache[b] = self.read_clim_band(src_clim, b)

        arrays, names = [], []
        for b in band_list:
            bl = b.lower()
            if bl in env_cache:
                arr = env_cache[bl]
            elif re.match(r'(?i)^bio\d{2}$', b):
                arr = clim_cache.get(b, None)
            elif bl == 'aspect':
                arr = env_cache.get('aspect', None)
            else:
                arr = None
            if arr is None:
                print(f"❗ Skipping unsupported band: {b}"); continue
            arrays.append(self.soft_fill(arr)); names.append(b)

        if not arrays:
            print("❗ No valid bands to write."); return False

        stacked = np.stack(arrays, axis=0)
        out_meta = clim_meta.copy()
        out_meta.update({'count': len(names), 'dtype': 'float32', 'nodata': self.config.NODATA_VAL})
        with rio.open(out_path, 'w', **out_meta) as dst:
            for i, nm in enumerate(names, 1):
                dst.write(stacked[i-1], i)
                dst.set_band_description(i, nm)
        print(f"✅ Stack saved: {out_path}  (bands: {names})")
        return True

    def build_stack_if_existing_current_interp(self, bands):
        if os.path.exists(self.config.WC_CURRENT_INTERP) and os.path.exists(self.config.ENV_1KM_INTERP):
            _ok = self.build_stack_dynamic(bands, self.config.CURRENT_STACK, self.config.WC_CURRENT_INTERP, self.config.ENV_1KM_INTERP)
        else:
            print("⏭️ Skipped building CURRENT stack (inputs missing).")

    def save_current_model_summary(self, train_bands, auc_mean, thr_best, data_dir, species_safe, scenario_model):
        """Save current model summary CSV."""
        cur_summary = pd.DataFrame([{
            "species": species_safe,
            "scenario_model": scenario_model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bands": "|".join(train_bands),
            "cv_auc_mean": round(auc_mean, 6),
            "threshold_youdenJ": round(thr_best, 6)
        }])
        cur_summary_path = os.path.join(data_dir, f"current_model_summary_{species_safe}.csv")
        cur_summary.to_csv(cur_summary_path, index=False)
        print("📝 Saved current model summary CSV:", cur_summary_path)


    def project_current_maps(self, pipe, thr_best, current_stack_path, current_prob_path, current_bin_path, nodata_val):
        """Project model over CURRENT stack to create probability and binary maps."""
        with rio.open(current_stack_path) as src:
            profile = src.profile.copy()
            desc = [d if d is not None else f"band{i}" for i,d in enumerate(src.descriptions,1)]
            arr = src.read().astype('float32')
            arr[arr == nodata_val] = np.nan
            Bc, H, W = arr.shape
            flat = arr.reshape(Bc, -1).T
            valid = ~np.isnan(flat).any(axis=1)
            probs_all = np.full(flat.shape[0], np.nan, dtype='float32')
            if np.any(valid):
                probs_all[valid] = pipe.predict_proba(flat[valid])[:, 1].astype('float32')
            prob_img = probs_all.reshape(H, W)

            prof_prob = profile.copy()
            prof_prob.update(count=1, dtype="float32", nodata=np.nan, compress='DEFLATE', predictor=2)
            with rio.open(current_prob_path, "w", **prof_prob) as dst:
                dst.write(prob_img, 1)

            bin_img = np.zeros((H, W), dtype="uint8")
            m = ~np.isnan(prob_img)
            bin_img[:, :] = 255
            bin_img[m] = (prob_img[m] >= thr_best).astype('uint8')

            prof_bin = profile.copy()
            prof_bin.update(count=1, dtype="uint8", nodata=255, compress='DEFLATE')
            with rio.open(current_bin_path, "w", **prof_bin) as dst:
                dst.write(bin_img, 1)

        print("✅ CURRENT suitability saved:\n ", current_prob_path, "\n ", current_bin_path)



    def train_current_rf_model(self, train_csv_path, current_stack_path, model_bundle_path,
                            data_dir, species_safe, scenario_model,
                            current_prob_path, current_bin_path, nodata_val):
        """Train CURRENT RF model and export current maps."""
        if not (os.path.exists(train_csv_path) and os.path.exists(current_stack_path)):
            if not os.path.exists(train_csv_path):
                print("❗ Training CSV not found:", train_csv_path)
            if not os.path.exists(current_stack_path):
                print("❗ CURRENT stack not found:", current_stack_path)
            return

        df = pd.read_csv(train_csv_path)
        with rio.open(current_stack_path) as _s:
            stack_band_names = [d if d is not None else f"band{i}" for i,d in enumerate(_s.descriptions,1)]
        train_bands = [b for b in stack_band_names if b in df.columns]
        missing_in_csv = [b for b in stack_band_names if b not in df.columns]
        if missing_in_csv:
            print("⚠️ These stack bands are absent in CSV and will be dropped:", missing_in_csv)

        X = df[train_bands].values
        y = df['PresAbs'].values.astype(int)

        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("rf", RandomForestClassifier(n_estimators=500, class_weight="balanced",
                                        n_jobs=-1, random_state=42, max_features="sqrt"))
        ])

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        aucs, thrs = [], []
        for tr, te in cv.split(X, y):
            with _silence_out, _silence_err:
                pipe.fit(X[tr], y[tr])
            p = pipe.predict_proba(X[te])[:, 1]
            aucs.append(roc_auc_score(y[te], p))
            fpr, tpr, thr = roc_curve(y[te], p)
            thrs.append(float(thr[np.argmax(tpr - fpr)]))
        auc_mean = float(np.mean(aucs))
        thr_best = float(np.median(thrs))
        print(f"CV ROC AUC mean: {auc_mean:.3f} | threshold: {thr_best:.3f}")

        with _silence_out, _silence_err:
            pipe.fit(X, y)
        dump({"model": pipe, "bands": train_bands, "threshold": thr_best,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            model_bundle_path)
        print("💾 Saved model to:", model_bundle_path)

        self.save_current_model_summary(train_bands, auc_mean, thr_best, data_dir, species_safe, scenario_model)
        self.project_current_maps(pipe, thr_best, current_stack_path, current_prob_path, current_bin_path, nodata_val)



    def train_multi_models(self, train_csv_path, current_stack_path, data_dir, species_safe, scenario_model):
        """Train multiple models and save each model bundle."""
        if not os.path.exists(train_csv_path):
            print("❗ Training CSV not found:", train_csv_path)
            return None, None, None, None, None, None

        df = pd.read_csv(train_csv_path)
        with rio.open(current_stack_path) as _s:
            stack_band_names = [d if d is not None else f"band{i}" for i,d in enumerate(_s.descriptions,1)]
        train_bands_final = [b for b in stack_band_names if b in df.columns]
        df = df.dropna(subset=train_bands_final + ['PresAbs'])
        X = df[train_bands_final].copy()
        y = df['PresAbs'].astype(int).values

        print('Training RFC and SVM')
        sm = SMOTE(random_state=42)
        X_res, y_res = sm.fit_resample(X, y)
        X_train, X_test, y_train, y_test = train_test_split(X_res, y_res, test_size=0.30, random_state=42, stratify=y_res)

        # Base models
        rf_base = RandomForestClassifier(n_estimators=500, min_samples_leaf=10, random_state=42, n_jobs=-1)
        svm     = SVC(probability=True, kernel='rbf', C=1.0, random_state=42)
        with _silence_out, _silence_err:
            rf_base.fit(X_train, y_train)
            svm.fit(X_train, y_train)

        def eval_model(m):
            y_pred = m.predict(X_test)
            if hasattr(m, "predict_proba"):
                y_prob = m.predict_proba(X_test)[:, 1]
            elif hasattr(m, "decision_function"):
                z = m.decision_function(X_test).astype('float32')
                zmin, zmax = np.nanmin(z), np.nanmax(z)
                y_prob = ((z - zmin) / (zmax - zmin)) if zmax > zmin else np.full_like(z, 0.5, dtype=float)
            else:
                y_prob = m.predict(X_test)
            return float(accuracy_score(y_test, y_pred)), float(roc_auc_score(y_test, y_prob))

        results_rows = []
        # Evaluate base models
        for nm, mdl in {"RandomForest": rf_base, "SVM": svm}.items():
            acc, auc = eval_model(mdl)
            results_rows.append({
                "species": species_safe, "scenario_model": scenario_model,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "model": nm, "features": "|".join(train_bands_final),
                "test_accuracy": round(acc, 6), "test_roc_auc": round(auc, 6),
                "cv_best_score": "", "best_params": ""
            })

        # Tuning
        print('Tuning SKF')
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        xgb_param = {
            'n_estimators':[100,300,500,800],'max_depth':[3,6,9,12],'learning_rate':[0.01,0.05,0.1,0.2],
            'subsample':[0.6,0.8,1.0],'colsample_bytree':[0.6,0.8,1.0],'reg_alpha':[0,0.1,1],'reg_lambda':[1,5,10]
        }
        lgb_param = {
            'n_estimators':[100,300,500,800],'num_leaves':[15,31,63,127],'learning_rate':[0.01,0.05,0.1,0.2],
            'subsample':[0.6,0.8,1.0],'colsample_bytree':[0.6,0.8,1.0],'reg_alpha':[0,0.1,1],'reg_lambda':[1,5,10]
        }
        cb_param  = {'iterations':[100,300,500],'depth':[4,6,8],'learning_rate':[0.01,0.05,0.1],'l2_leaf_reg':[1,3,5,7]}
        print('Tuning XGBClassifier')
        xgb = XGBClassifier(random_state=42, eval_metric='logloss', verbosity=0)
        print('Tuning RSCV')
        xgb_search = RandomizedSearchCV(xgb, xgb_param, n_iter=50, scoring='accuracy', cv=cv, n_jobs=-1, verbose=0, random_state=42)
        with _silence_out, _silence_err: xgb_search.fit(X_train, y_train)
        best_xgb = xgb_search.best_estimator_
        acc, auc = eval_model(best_xgb)
        results_rows.append({
            "species": species_safe, "scenario_model": scenario_model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": "XGBoost (tuned)", "features": "|".join(train_bands_final),
            "test_accuracy": round(acc, 6), "test_roc_auc": round(auc, 6),
            "cv_best_score": round(float(xgb_search.best_score_), 6),
            "best_params": json.dumps(xgb_search.best_params_)
        })

        print('Tuning LGBMC')
        lgb = LGBMClassifier(random_state=42, verbosity=-1, force_col_wise=True, n_jobs=2)
        print('RandomizedSearchCV for LGBM')
        lgb_search = RandomizedSearchCV(lgb, lgb_param, n_iter=50, scoring='accuracy', cv=cv, n_jobs=7, verbose=0, random_state=42)
        print('Fitting LGBM RSCV')
        with _silence_out, _silence_err: lgb_search.fit(X_train, y_train)

        best_lgb = lgb_search.best_estimator_
        print('Evaluating best LGBM')
        acc, auc = eval_model(best_lgb)
        results_rows.append({
            "species": species_safe, "scenario_model": scenario_model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": "LightGBM (tuned)", "features": "|".join(train_bands_final),
            "test_accuracy": round(acc, 6), "test_roc_auc": round(auc, 6),
            "cv_best_score": round(float(lgb_search.best_score_), 6),
            "best_params": json.dumps(lgb_search.best_params_)
        })

        print('Tuning CatBoostClassifier')

        cb = CatBoostClassifier(random_state=42, verbose=0)
        cb_search = RandomizedSearchCV(cb, cb_param, n_iter=30, scoring='accuracy', cv=cv, n_jobs=7, verbose=0, random_state=42)
        with _silence_out, _silence_err: cb_search.fit(X_train, y_train)
        best_cb = cb_search.best_estimator_
        acc, auc = eval_model(best_cb)
        results_rows.append({
            "species": species_safe, "scenario_model": scenario_model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": "CatBoost (tuned)", "features": "|".join(train_bands_final),
            "test_accuracy": round(acc, 6), "test_roc_auc": round(auc, 6),
            "cv_best_score": round(float(cb_search.best_score_), 6),
            "best_params": json.dumps(cb_search.best_params_)
        })

        # Ensemble (soft voting)
        print('Ensenble VotingClassifier')

        ev = VotingClassifier(estimators=[('xgb', best_xgb), ('lgb', best_lgb), ('cb', best_cb)], voting='soft')
        with _silence_out, _silence_err: ev.fit(X_train, y_train)
        acc, auc = eval_model(ev)
        results_rows.append({
            "species": species_safe, "scenario_model": scenario_model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": "Ensemble (XGB+LGBM+CatBoost)", "features": "|".join(train_bands_final),
            "test_accuracy": round(acc, 6), "test_roc_auc": round(auc, 6),
            "cv_best_score": "", "best_params": ""
        })

        # Create models dictionary
        models = {'RandomForest': rf_base, 'SVM': svm}

        # Save consolidated CSV to data_<species>
        results_df = pd.DataFrame(results_rows)
        out_csv = os.path.join(data_dir, f"models_results_{species_safe}_{scenario_model}.csv")
        results_df.to_csv(out_csv, index=False)
        print("📝 Saved model results CSV:", out_csv)

        # Save each model bundle to data_<species>
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        bundles = {
            os.path.join(data_dir, f"model_RF_{species_safe}.joblib"):
                {"model": rf_base, "bands": train_bands_final, "timestamp_utc": ts, "notes":"RandomForest (SMOTE-resampled)"},
            os.path.join(data_dir, f"model_SVM_{species_safe}.joblib"):
                {"model": svm, "bands": train_bands_final, "timestamp_utc": ts, "notes":"SVM RBF (SMOTE-resampled)"},
            os.path.join(data_dir, f"model_XGB_{species_safe}.joblib"):
                {"model": best_xgb, "bands": train_bands_final, "timestamp_utc": ts, "notes":"XGBoost tuned (SMOTE-resampled)"},
            os.path.join(data_dir, f"model_LGBM_{species_safe}.joblib"):
                {"model": best_lgb, "bands": train_bands_final, "timestamp_utc": ts, "notes":"LightGBM tuned (SMOTE-resampled)"},
            os.path.join(data_dir, f"model_CatBoost_{species_safe}.joblib"):
                {"model": best_cb, "bands": train_bands_final, "timestamp_utc": ts, "notes":"CatBoost tuned (SMOTE-resampled)"},
            os.path.join(data_dir, f"model_Ensemble_{species_safe}.joblib"):
                {"model": ev, "bands": train_bands_final, "timestamp_utc": ts, "notes":"Soft-voting ensemble XGB+LGBM+CatBoost"}
        }
        for path, obj in bundles.items():
            dump(obj, path)
            print("💾 Saved:", path)

        return models, best_xgb, best_lgb, best_cb, ev, train_bands_final


    def find_future_tif(self, model, ssp, period, roots):
        """Find future TIFF file in multiple directory roots."""
        rel = self.config.FUTURE_TIF_REL_TEMPLATE.format(model=model, ssp=ssp, period=period)

        for r in roots:
            cand = os.path.join(r, rel)
            if os.path.exists(cand):
                return cand
        return None


    def _predict_proba_safe(self, model, Xdf):
        """Safely predict probabilities for any model type."""
        if hasattr(model, "predict_proba"):
            return model.predict_proba(Xdf)[:, 1].astype('float32')
        if hasattr(model, "decision_function"):
            z = model.decision_function(Xdf).astype('float32')
            zmin, zmax = np.nanmin(z), np.nanmax(z)
            return ((z - zmin) / (zmax - zmin)).astype('float32') if zmax > zmin else np.full(z.shape, 0.5, dtype='float32')
        yhat = model.predict(Xdf).astype('float32')
        return np.clip(yhat, 0, 1).astype('float32')


    def load_models_if_needed(self, data_dir, species_safe):
        """Load models from data directory if not already in memory."""
        try:
            train_bands_final = load(os.path.join(data_dir, f"model_RF_{species_safe}.joblib"))["bands"]
            models = {
                'RandomForest': load(os.path.join(data_dir, f"model_RF_{species_safe}.joblib"))["model"],
                'SVM':          load(os.path.join(data_dir, f"model_SVM_{species_safe}.joblib"))["model"],
            }
            best_xgb = load(os.path.join(data_dir, f"model_XGB_{species_safe}.joblib"))["model"]
            best_lgb = load(os.path.join(data_dir, f"model_LGBM_{species_safe}.joblib"))["model"]
            best_cb  = load(os.path.join(data_dir, f"model_CatBoost_{species_safe}.joblib"))["model"]
            ev       = load(os.path.join(data_dir, f"model_Ensemble_{species_safe}.joblib"))["model"]
            print("Loaded models from data folder.")
            return models, best_xgb, best_lgb, best_cb, ev, train_bands_final
        except Exception as e:
            print("Could not load saved models:", e)
            return None, None, None, None, None, None

    def process_future_maps(self, scenarios, periods, scenario_model, future_tif_roots, aoi_gdf_wgs84,
                        input_dir, env_1km_interp, bands, data_dir, species_safe, species_dir,
                        nodata_val, default_bin_thr, models=None, best_xgb=None, best_lgb=None,
                        best_cb=None, ev=None, train_bands_final=None):
        """Process future maps for all scenarios and periods."""
        # Load models if not provided
        if models is None:
            models, best_xgb, best_lgb, best_cb, ev, train_bands_final = self.load_models_if_needed(data_dir, species_safe)

        if models is None:
            print("Models not trained/loaded; skipping exports.")
            return

        # Create models dictionary for export
        models_to_export = {
            'RandomForest': models['RandomForest'],
            'XGBoost': best_xgb,
            'LightGBM': best_lgb,
            'CatBoost': best_cb,
            'SVM': models['SVM'],
            'Ensemble': ev
        }

        for ssp in scenarios:
            for period in periods:
                future_tif_global = self.find_future_tif(scenario_model, ssp, period, future_tif_roots)
                if future_tif_global is None:
                    print(f"Future global tif not found for {ssp} {period} in any root.")
                    continue

                future_stack = self.prepare_future_stack(
                    future_tif_global, aoi_gdf_wgs84, input_dir, scenario_model, ssp, period,
                    env_1km_interp, bands, nodata_val
                )

                if future_stack is not None:
                    self.export_future_maps(
                        future_stack, train_bands_final, models_to_export, species_dir,
                        scenario_model, ssp, period, nodata_val, default_bin_thr
                    )


    def prepare_future_stack(self, future_tif_global, aoi_gdf_wgs84, input_dir, scenario_model, ssp, period,
                            env_1km_interp, bands, nodata_val):
        """Prepare future stack by clipping, interpolating, and building stack."""
        with rio.open(future_tif_global) as src:
            r_crs = src.crs
        gdf_clip = aoi_gdf_wgs84.to_crs(r_crs) if aoi_gdf_wgs84.crs != r_crs else aoi_gdf_wgs84
        geoms = [mapping(geom) for geom in gdf_clip.geometry]

        with rio.open(future_tif_global) as src:
            out_image, out_transform = mask(src, geoms, crop=True)
            out_meta = src.meta.copy()
            out_meta.update({"driver":"GTiff","height":out_image.shape[1],"width":out_image.shape[2],
                            "transform":out_transform})

        fut_clipped = os.path.join(input_dir, f"bioc_{scenario_model}_{ssp}_{period}.tif")
        with rio.open(fut_clipped, "w", **out_meta) as dst:
            dst.write(out_image)
        print("✅ Clipped future raster:", fut_clipped)

        fut_interp = os.path.join(input_dir, f"bioc_{scenario_model}_{ssp}_{period}_Interpolated.tif")
        self.interpolate_raster_nearest_fast(fut_clipped, fut_interp)
        print("✅ Interpolated future raster:", fut_interp)

        # Build FUTURE stack with same BANDS
        future_stack = os.path.join(input_dir, f"FuturePredictorsSubset_1km_Interpolated_{ssp}_{period}.tif")
        if os.path.exists(fut_interp) and os.path.exists(env_1km_interp):
            ok = self.build_stack_dynamic(bands, future_stack, fut_interp, env_1km_interp)
            if not ok:
                print("❗ Could not build future stack; skipping.")
                return None
        else:
            if not os.path.exists(fut_interp):
                print("❗ Missing:", fut_interp)
            if not os.path.exists(env_1km_interp):
                print("❗ Missing:", env_1km_interp)
            return None

        return future_stack


    def export_future_maps(self, future_stack_path, train_bands_final, models_dict, species_dir,
                        scenario_model, ssp, period, nodata_val, default_bin_thr):
        """Export probability and binary maps for all models."""
        fut_parent = os.path.join(species_dir, scenario_model, ssp, period)
        fut_prob_dir = os.path.join(fut_parent, "probability")
        fut_bin_dir = os.path.join(fut_parent, "binary")
        os.makedirs(fut_prob_dir, exist_ok=True)
        os.makedirs(fut_bin_dir, exist_ok=True)

        with rio.open(future_stack_path) as src:
            meta = src.meta.copy()
            band_names = [d if d is not None else f"band{i}" for i,d in enumerate(src.descriptions,1)]
            data = src.read().astype('float32')
            data[data == nodata_val] = np.nan
            height, width = src.height, src.width

        cols_to_use = [b for b in train_bands_final if b in band_names]
        if not cols_to_use:
            print("❗ No overlapping bands; skipping.")
            return

        idxs = [band_names.index(b) for b in cols_to_use]
        sub = data[np.array(idxs), :, :]
        flat = sub.reshape(len(idxs), -1).T
        valid_mask = ~np.isnan(flat).any(axis=1)
        flat_df = pd.DataFrame(flat, columns=cols_to_use)

        for name, mdl in models_dict.items():
            probs_all = np.full(flat_df.shape[0], np.nan, dtype='float32')
            if np.any(valid_mask):
                with _silence_out, _silence_err:
                    probs_all[valid_mask] = self._predict_proba_safe(mdl, flat_df.iloc[valid_mask])

            prob_raster = probs_all.reshape(height, width)

            out_prob = os.path.join(fut_prob_dir, f'Future_Suitability_Prob_{name}.tif')
            prob_meta = meta.copy()
            prob_meta.update({'count':1,'dtype':'float32','nodata':np.nan,'compress':'deflate','predictor':3})
            with rio.open(out_prob, 'w', **prob_meta) as dst:
                dst.write(prob_raster, 1)
            print("✔ Probability:", out_prob)

            binary_all = np.full(flat_df.shape[0], 255, dtype='uint8')
            if np.any(valid_mask):
                binary_all[valid_mask] = (probs_all[valid_mask] >= default_bin_thr).astype('uint8')
            bin_raster = binary_all.reshape(height, width)

            out_bin = os.path.join(fut_bin_dir, f'Future_Suitability_Bin_{name}.tif')
            bin_meta = meta.copy()
            bin_meta.update({'count':1,'dtype':'uint8','nodata':255,'compress':'lzw'})
            with rio.open(out_bin, 'w', **bin_meta) as dst:
                dst.write(bin_raster, 1)
            print("✔ Binary     :", out_bin)

        print("✅ All future maps exported under:")
        print(f"  {os.path.join(species_dir, scenario_model, ssp, period)}\n   ├── probability\n   └── binary")


    def clip_future_raster(self, future_tif_global, input_dir, gcm_model, scenario, period, aoi_shp):
        """Clip future raster to AOI boundary."""
        fut_clipped = os.path.join(input_dir, f"bioc_{gcm_model}_{scenario}_{period}.tif")
        fut_interp = os.path.join(input_dir, f"bioc_{gcm_model}_{scenario}_{period}_Interpolated.tif")
        fut_stack = os.path.join(input_dir, f"FuturePredictorsSubset_1km_Interpolated_{scenario}_{period}.tif")

        assert os.path.exists(future_tif_global), f"Future TIF not found: {future_tif_global}"

        aoi_gdf = gpd.read_file(aoi_shp)
        if aoi_gdf.crs is None:
            aoi_gdf = aoi_gdf.set_crs("EPSG:4326")

        with rio.open(future_tif_global) as src:
            fut_crs = src.crs
            aoi_crs = aoi_gdf.to_crs(fut_crs)
            geoms = [mapping(geom) for geom in aoi_crs.geometry]
            out_image, out_transform = mask(src, geoms, crop=True)
            out_meta = src.meta.copy()
            out_meta.update(driver="GTiff", height=out_image.shape[1], width=out_image.shape[2], transform=out_transform)

        with rio.open(fut_clipped, "w", **out_meta) as dst:
            dst.write(out_image)
        print("✅ Clipped:", fut_clipped)

        return fut_clipped, fut_interp, fut_stack


    def interpolate_raster_nearest_fast(self, in_tif, out_tif):
        with rio.open(in_tif) as src:
            meta = src.meta.copy()
            nd = src.nodata
            out = []
            for b in range(1, src.count + 1):
                data = src.read(b).astype("float32")
                mask_ = np.isnan(data) if nd is None or (isinstance(nd, float) and np.isnan(nd)) else (data == nd)
                if mask_.any():
                    # nearest fill via indices from distance transform
                    _, idx = ndimage.distance_transform_edt(mask_, return_distances=True, return_indices=True)
                    data[mask_] = data[tuple(idx)][mask_]
                out.append(data)
            with rio.open(out_tif, "w", **meta) as dst:
                for i, arr in enumerate(out, 1):
                    dst.write(arr, i)
        print("✅ Interpolated:", in_tif)


    def clipand_interpolate_future_raster_for_all(self, data_dir, input_dir, scenarios, periods, scenario_model, future_tif_roots, spec_safe):
        aoi_shp = self.find_aoi_shapefile(data_dir, spec_safe)
        for ssp in scenarios:
            for period in periods:
                future_tif_global = self.find_future_tif(scenario_model, ssp, period, future_tif_roots)
                if future_tif_global is None:
                    print(f"❗ Future global tif not found for {ssp} {period} in any root.")
                    continue

                fut_clipped, fut_interp, fut_stack = self.clip_future_raster(future_tif_global, input_dir, scenario_model, ssp, period, aoi_shp)

                self.interpolate_raster_nearest_fast(fut_clipped, fut_interp)


    def load_models(self, data_dir, species_safe):
        """Load all trained models from joblib files."""
        model_files = {
            "RandomForest": os.path.join(data_dir, f"model_RF_{species_safe}.joblib"),
            "SVM":          os.path.join(data_dir, f"model_SVM_{species_safe}.joblib"),
            "XGBoost":      os.path.join(data_dir, f"model_XGB_{species_safe}.joblib"),
            "LightGBM":     os.path.join(data_dir, f"model_LGBM_{species_safe}.joblib"),
            "CatBoost":     os.path.join(data_dir, f"model_CatBoost_{species_safe}.joblib"),
            "Ensemble":     os.path.join(data_dir, f"model_Ensemble_{species_safe}.joblib"),
        }

        models = {}
        train_bands_final = None
        for name, path in model_files.items():
            if os.path.exists(path):
                bundle = load(path)
                models[name] = bundle["model"]
                if train_bands_final is None:
                    train_bands_final = bundle["bands"]
                print("Loaded model:", name)

        assert models, "No saved models found in the data folder."
        return models, train_bands_final


    def prepare_future_stack_data(self, future_stack_path, train_bands_final, nodata_val):
        """Prepare future stack data for prediction."""
        with rio.open(future_stack_path) as src:
            meta = src.meta.copy()
            band_names = [d if d else f"band{i}" for i,d in enumerate(src.descriptions,1)]
            data = src.read().astype("float32")
            data[data == nodata_val] = np.nan
            H, W = src.height, src.width

        cols_to_use = [b for b in (train_bands_final or []) if b in band_names]
        assert cols_to_use, "No overlapping bands between trained models and future stack."
        idxs = [band_names.index(b) for b in cols_to_use]
        sub  = data[np.array(idxs), :, :]
        flat = sub.reshape(len(idxs), -1).T
        valid_mask = ~np.isnan(flat).any(axis=1)
        flat_df = pd.DataFrame(flat, columns=cols_to_use)

        return meta, H, W, flat_df, valid_mask


    def export_meta_and_raster_to_json_dict(self, raster_data, meta):
        meta_copy = meta.copy()
        meta_copy['crs'] = meta.get('crs').wkt
        # Create JSON data structure
        json_data = {
            'meta':  meta_copy,
            'raster': raster_data.tolist(),
            'summary_stats': {
                'mean_habitat_suitability': float(np.mean(raster_data)),
                'std_habitat_suitability': float(np.std(raster_data))
            },
        }
        return json_data


    def export_meta_and_raster_to_json(self, raster_data, meta, output_path):
        """Export raster data and metadata as JSON file alongside the GeoTIFF."""

        # Create JSON data structure
        json_data = self.export_meta_and_raster_to_json_dict(raster_data, meta)

        # Save JSON file
        json_path = output_path.replace('.tif', '.json')
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)

        print(f"✔ JSON metadata: {json_path}")
        return json_data


    def export_models_predictions(self, models, flat_df, valid_mask, H, W, meta,
                            fut_prob_dir, fut_bin_dir, default_bin_thr):
        """Export probability and binary predictions for all models."""
        for name, mdl in models.items():
            print("Predicting:", name)
            probs_all = np.full(flat_df.shape[0], np.nan, dtype="float32")
            if np.any(valid_mask):
                probs_all[valid_mask] = self._predict_proba_safe(mdl, flat_df.iloc[valid_mask])
            prob_raster = probs_all.reshape(H, W)

            prob_meta = meta.copy()
            prob_meta.update(count=1, dtype="float32", nodata=np.nan, compress="DEFLATE", predictor=3)
            out_prob = os.path.join(fut_prob_dir, f"Future_Suitability_Prob_{name}.tif")
            with rio.open(out_prob, "w", **prob_meta) as dst:
                dst.write(prob_raster, 1)
            prob_json_output = self.export_meta_and_raster_to_json(prob_raster, prob_meta, out_prob)
            print("✔ Probability:", out_prob)

            binary_all = np.full(flat_df.shape[0], 255, dtype="uint8")
            if np.any(valid_mask):
                binary_all[valid_mask] = (probs_all[valid_mask] >= default_bin_thr).astype("uint8")
            bin_raster = binary_all.reshape(H, W)

            bin_meta = meta.copy()
            bin_meta.update(count=1, dtype="uint8", nodata=255, compress="LZW")
            out_bin = os.path.join(fut_bin_dir, f"Future_Suitability_Bin_{name}.tif")
            with rio.open(out_bin, "w", **bin_meta) as dst:
                dst.write(bin_raster, 1)

            self.export_meta_and_raster_to_json(bin_raster, bin_meta, out_bin)
            print("✔ Binary     :", out_bin)


    def run_model_prob_prediction(self, model_name, model, flat_df, valid_mask, H, W, meta):
        """run probability predictions for only a model."""
        name = model_name
        mdl = model
        print("Predicting:", name)
        probs_all = np.full(flat_df.shape[0], np.nan, dtype="float32")
        if np.any(valid_mask):
            probs_all[valid_mask] = self._predict_proba_safe(mdl, flat_df.iloc[valid_mask])
        prob_raster = probs_all.reshape(H, W)

        prob_meta = meta.copy()
        prob_meta.update(count=1, dtype="float32", nodata=np.nan, compress="DEFLATE", predictor=3)
        prob_json_output = self.export_meta_and_raster_to_json_dict(prob_raster, prob_meta)
        return prob_json_output



    def predict_and_export_future_maps(self, data_dir, species_safe, future_stack_path,
                                    fut_prob_dir, fut_bin_dir, nodata_val, default_bin_thr):
        """Main function to load models and export future predictions."""
        # Load models
        models, train_bands_final = self.load_models(data_dir, species_safe)


        # Prepare future stack data
        meta, H, W, flat_df, valid_mask = self.prepare_future_stack_data(
            future_stack_path, train_bands_final, nodata_val
        )

        # Export predictions
        prob_json_output = self.export_models_predictions(
            models, flat_df, valid_mask, H, W, meta,
            fut_prob_dir, fut_bin_dir, default_bin_thr
        )

        print("\n🎉 DONE.\nProbability:", fut_prob_dir, "\nBinary:", fut_bin_dir)
        return prob_json_output


    def predict_and_export_future_maps_for_all(self, data_dir, input_dir, species_dir, scenario_model, scenarios, periods, species_safe, default_bin_thr):
        for ssp in scenarios:
            for period in periods:
                fut_parent   = os.path.join(species_dir, scenario_model, ssp, period)
                fut_prob_dir = os.path.join(fut_parent, "probability")
                fut_bin_dir  = os.path.join(fut_parent, "binary")
                for d in [species_dir, input_dir, fut_parent, fut_prob_dir, fut_bin_dir]:
                    os.makedirs(d, exist_ok=True)

                fut_stack = os.path.join(input_dir, f"FuturePredictorsSubset_1km_Interpolated_{ssp}_{period}.tif")

                self.predict_and_export_future_maps(
                    data_dir=data_dir,
                    species_safe=species_safe,
                    future_stack_path=fut_stack,
                    fut_prob_dir=fut_prob_dir,
                    fut_bin_dir=fut_bin_dir,
                    nodata_val=self.config.NODATA_VAL,
                    default_bin_thr=default_bin_thr
                )


    def predict_future_species_suitability(self, data_dir, input_dir, scenarios, periods, species_safe, summary_only=False):
        models, train_bands_final = self.load_models(data_dir, species_safe)
        model_name = 'Ensemble'
        ensamble_model = models.get(model_name)
        ret_dict = {
            'species': species_safe,
            'scenarios': {},
            'meta': {},
            # 'region' wkt?
        }
        for ssp in scenarios:
            ret_dict['scenarios'][ssp] = {
                'periods': {}
            }
            for period in periods:

                fut_stack = os.path.join(input_dir, f"FuturePredictorsSubset_1km_Interpolated_{ssp}_{period}.tif")
                # Prepare future stack data
                meta, H, W, flat_df, valid_mask = self.prepare_future_stack_data(
                    fut_stack, train_bands_final, self.config.NODATA_VAL
                )

                prob_json_output = self.run_model_prob_prediction(
                    model_name=model_name,
                    model=ensamble_model,
                    flat_df=flat_df,
                    valid_mask=valid_mask,
                    H=H,
                    W=W,
                    meta=meta
                )
                prob_meta = prob_json_output.pop('meta', {})
                if summary_only:
                    prob_json_output = {
                        'summary_stats': prob_json_output['summary_stats']
                    }
                ret_dict['scenarios'][ssp]['periods'][period] = prob_json_output
                ret_dict['meta'] = prob_meta
        return ret_dict
