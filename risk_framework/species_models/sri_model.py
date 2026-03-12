import numpy as np
import requests


from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY,
)

from risk_framework.web_api.models.operations import (
    retrieve_or_calculate_hsi_future_or_current,
)
from risk_framework.web_api.utils import generate_geo_uuid, get_country_wkt


url = "http://localhost:8000/api/v1/predict-future-habitat-suitability/"


class SRIBaseModel(object):
    def __init__(self, country_code, wkt_polygon, db):
        self.country_code = country_code
        self.wkt_polygon = wkt_polygon
        if wkt_polygon is None or wkt_polygon == "":
            self.wkt_polygon = get_country_wkt(country_code)
        self.species_list = self.get_species_list()
        self.geo_id = generate_geo_uuid(
            self.species_list, self.country_code, self.wkt_polygon
        )
        self.db = db

    def get_species_list(self):
        species_list = INDICATOR_SP_PER_COUNTRY.get(self.country_code, [])
        species_list.sort()
        return species_list

    def get_hsi_and_meta_for_one_species(self, species_name, climate_scenario, climate_model, period):
        is_future = True
        if period.lower() == "current":
            is_future = False
        hsi_geo_id = generate_geo_uuid([species_name], self.country_code, self.wkt_polygon)
        species_hsi = retrieve_or_calculate_hsi_future_or_current(
            species_name,
            self.country_code,
            self.wkt_polygon,
            hsi_geo_id,
            climate_scenario,
            climate_model,
            period,
            self.db,
            future=is_future,
        )
        meta = species_hsi.meta
        meta_dtype = np.dtype(meta['dtype'])

        raster_array = np.array(species_hsi.raster_data.raster, dtype=meta_dtype)
        return raster_array, meta

    def species_hsi_aggregation_method(self, list_of_species_hsi):
        raise NotImplementedError()

    def align_rasters(self, species_rasters, species_metas):
        """
        Align all rasters to the reference raster shape and bounds
        """
        reference_meta = species_metas[0]
        h = reference_meta['height']
        w = reference_meta['width']
        aligned_rasters = []

        # Create reference transform
        ref_transform = from_origin(
            reference_meta['transform'][2],
            reference_meta['transform'][5],
            reference_meta['transform'][0],
            abs(reference_meta['transform'][4])
        )
        aligned_rasters.append(species_rasters[0])
        for raster, meta in zip(species_rasters[1:], species_metas[1:]):
            # Create destination array with reference shape
            dest = np.full((h, w), -1, dtype=np.float32)

            # Create source transform
            src_transform = from_origin(
                meta['transform'][2],
                meta['transform'][5],
                meta['transform'][0],
                abs(meta['transform'][4])
            )

            # Simple reprojection
            reproject(
                source=raster,
                destination=dest,
                src_transform=src_transform,
                src_crs=meta['crs'],
                src_nodata=-1,  # <-- ADD THIS
                dst_transform=ref_transform,
                dst_crs=reference_meta['crs'],
                dst_nodata=-1,  # <-- ADD THIS
                resampling=Resampling.bilinear
            )

            aligned_rasters.append(dest)

        return aligned_rasters

    def run(self, climate_scenario, climate_model, period):
        # if current prediction
        if climate_scenario is None:
            climate_scenario = 'current'
            period = climate_scenario

        list_of_species_hsi = []
        list_of_species_meta = []
        for species_name in self.species_list:
            import ipdb; ipdb.set_trace()
            species_hsi, meta = self.get_hsi_and_meta_for_one_species(species_name, climate_scenario, climate_model, period)
            list_of_species_hsi.append(species_hsi)
            list_of_species_meta.append(meta)

        default_meta = list_of_species_meta[0]
        # list_of_species_hsi_aligned = self.align_rasters(list_of_species_hsi, list_of_species_meta)

        # sri_raster = self.species_hsi_aggregation_method(list_of_species_hsi)
        sri_raster = list_of_species_hsi[0].tolist()
        return {
            "species_list": self.species_list,
            "country": self.country_code,
            "scenario": climate_scenario,
            "period": period,
            "raster_data": {
                "raster": sri_raster
            },
            'meta': default_meta,
            'logic_type': None,
            'correction_method': None,
        }



class FuzzySRIModel(SRIBaseModel):
    def species_hsi_aggregation_method(self, list_of_species_hsi):
        stacked = np.stack(list_of_species_hsi)
        # Calculate fuzzy mean (mean across species axis)
        fuzzy_mean = np.mean(stacked, axis=0)

        return fuzzy_mean.tolist()

    def run(self, climate_scenario, climate_model, period):
        data = super().run(climate_scenario, climate_model, period)
        data['logic_type'] = 'fuzzy'
        return data


if __name__ == '__main__':
    import json
    import rasterio

    from risk_framework.web_api.utils import get_db
    country_code = 'NL'
    db = list(get_db())[0]
    fsri = FuzzySRIModel(country_code, wkt_polygon=None, db=db)

    result = fsri.run(climate_scenario='ssp245', climate_model='EC-Earth3-Veg', period='2021-2040')


    meta = result['meta']
    dtype = meta['dtype']
    # predictor = meta['predictor']
    compress = meta['compress']
    raster_value = result['raster_data']['raster']
    # raster_value = out_image[0]  # Remove the band dimension
    raster = np.array(raster_value, dtype=np.dtype(dtype))
    # Create transform object for rasterio
    # transform = from_origin(
    #     meta['transform'][2],  # top-left x
    #     meta['transform'][5],  # top-left y
    #     meta['transform'][0],  # pixel width
    #     # abs(meta['transform'][4])  # pixel height (make positive)
    #     abs(meta['transform'][4])  # pixel height (make positive)
    # )
    # # Save as GeoTIFF - rasterio handles the transform directly
    with rasterio.open(
        'probability_raster_fsri.tif',
        'w',
        driver='GTiff',
        height=raster.shape[0],
        width=raster.shape[1],
        count=1,
        dtype=raster.dtype,
        crs=meta['crs'],
        transform=meta['transform'],  # rasterio accepts the affine directly
        nodata=-1
    ) as dst:
        dst.write(raster, 1)
    print(json.dumps(result, indent=4))
