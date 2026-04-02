import os

from shapely.geometry import box
import numpy as np
import pycountry
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling

from risk_framework.conf import ee, GLC_FILE_FORMAT, BASE_RESOLUTION, GLC_YEAR
import geemap

from risk_framework.web_api.utils import get_country_wkt


class GLCModel(object):
    def __init__(self,country_code):
        self.country_code = country_code
        self.wkt_polygon = get_country_wkt(country_code)
        self.glc_raster_path = GLC_FILE_FORMAT.format(country_code=self.country_code, year=GLC_YEAR)
        self.final_nodata = -1
        self.final_dtype = np.int16
        self.country_name = pycountry.countries.get(alpha_2=country_code).name

    def remap_to_groups_ee(self, image):
        """Remap detailed classes to groups 0..2.
        -1 is to ignore/remove, 0 is green (and ice) 1 is urban
        """
        def to_group(c):
            cropland = [10,11,12,20]
            forest = [51,52,61,62,71,72,81,82,91,92]
            shrubland = [120,121,122]
            grassland = [130,140,150,152,153]
            wetland = [181,182,183,184,185,186,187]
            urban = [190]
            bare = [200,201,202]
            water = [210]
            ice = [220]
            filled = [0]

            green_land = cropland + forest + shrubland + grassland + wetland + ice
            urban_land = urban
            removed = bare + water + filled

            if c in removed:
                return self.final_nodata
            if c in green_land:
                return 0
            if c in urban_land:
                return 1

        codes = [0, 10, 11, 12, 20, 51, 52, 61, 62, 71, 72, 81, 82, 91, 92,
                120, 121, 122, 130, 140, 150, 152, 153, 181, 182, 183, 184,
                185, 186, 187, 190, 200, 201, 202, 210, 220]
        group_map = [to_group(c) for c in codes]

        return image.remap(codes, group_map, self.final_nodata).rename('group').toInt16()

    def get_country_bbox(self):
        country = (ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
                .filter(ee.Filter.eq('country_na', self.country_name))
                .geometry())

        bounds = country.bounds().getInfo()['coordinates'][0]
        minx, miny = bounds[0]
        maxx, maxy = bounds[2]


        return ee.Geometry.Rectangle([minx, miny, maxx, maxy])


    def retrieve_ee_data(self):
        bbox = self.get_country_bbox()

        # Get annual collection and mosaic to single multi-band image
        annual_ic = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
        annual_mosaic = annual_ic.mosaic()

        # Rename bands to years (2000-2022)
        annual_years = ee.List.sequence(2000, 2022).map(lambda y: ee.Number(y).format('%04d'))
        annual_renamed = annual_mosaic.rename(annual_years)

        # Select the 2020 band
        classification = annual_renamed.select([str(GLC_YEAR)]).rename('classification')

        # Remap to groups
        grouped = self.remap_to_groups_ee(classification)

        # # Download
        # url = grouped.getDownloadURL({
        #     'region': bbox,
        #     'scale': BASE_RESOLUTION,
        #     'crs': 'EPSG:4326',
        #     'format': 'GeoTIFF'
        # })


        geemap.ee_export_image(
            grouped,
            filename=self.glc_raster_path,
            scale=BASE_RESOLUTION,
            region=bbox,
            crs='EPSG:4326'
        )

    def load_glc_raster_and_meta(self):
        if not os.path.exists(self.glc_raster_path):
            self.retrieve_ee_data()
        with rasterio.open(self.glc_raster_path) as glc_src:
            raster_array = glc_src.read(1)
            raster_array[raster_array == glc_src.nodata] = self.final_nodata
            raster_meta = glc_src.profile.copy()
            raster_meta['nodata'] = self.final_nodata
            return raster_array, raster_meta

    def reproject_to_base(self, reference_meta, glc_raster, glc_meta):
        h = reference_meta['height']
        w = reference_meta['width']

        # Create reference transform
        ref_transform = from_origin(
            reference_meta['transform'][2],
            reference_meta['transform'][5],
            reference_meta['transform'][0],
            abs(reference_meta['transform'][4])
        )
        # Create source transform
        src_transform = from_origin(
            glc_meta['transform'][2],
            glc_meta['transform'][5],
            glc_meta['transform'][0],
            abs(glc_meta['transform'][4])
        )

        dest = np.full((h, w), reference_meta['nodata'], dtype=reference_meta['dtype'])
        # Simple reprojection
        reproject(
            source=glc_raster,
            destination=dest,
            src_transform=src_transform,
            src_crs=glc_meta['crs'],
            src_nodata=glc_meta['nodata'],
            dst_transform=ref_transform,
            dst_crs=reference_meta['crs'],
            dst_nodata=reference_meta['nodata'],
            resampling=Resampling.nearest
        )

        glc_meta.update({
            'crs': reference_meta['crs'],
            'nodata': reference_meta['nodata'],
            'transform': ref_transform,
            'width': w,
            'height': h
        })

        return dest, glc_meta

    def get_reproj_to_reference(self, reference_meta):
        print('Running GLC model.')
        glc_raster, glc_meta = self.load_glc_raster_and_meta()
        return self.reproject_to_base(reference_meta, glc_raster, glc_meta)

    def add_mask_to_reference(self, reference_raster, ori_reference_meta, glc_raster=None, glc_meta=None, glc_mask_value=None):
        """
        returns copy of reference raster, but removes from it raster values from positions that are in
         the glc mask value (-1 by default)
        GLC values are:
            -1 is to ignore/remove, 0 is green (and ice) 1 is urban
        """
        reference_meta = ori_reference_meta.copy()
        if glc_raster is None or glc_meta is None:
            glc_raster, glc_meta = self.get_reproj_to_reference(reference_meta)
        if glc_mask_value is None:
            glc_mask_value = glc_meta['nodata']
        glc_mask = glc_raster == glc_mask_value
        mask_raster = reference_raster.copy()
        mask_raster[glc_mask] = reference_meta['nodata']
        return mask_raster

    def run(self, reference_raster, reference_meta):
        print('Running GLC model.')
        glc_raster, glc_meta = self.load_glc_raster_and_meta()
        if reference_raster and reference_meta:
            self.reproject_to_base(reference_meta, glc_raster, glc_meta)
        # glc_meta['crs'] = str(glc_meta['crs'])
        # valid_mask = glc_raster != glc_meta['nodata']
        # mean_raster_value = float(np.mean(glc_raster[valid_mask]))
        # std_raster_value =  float(np.std(glc_raster[valid_mask]))
        return glc_raster, glc_meta




if __name__ == '__main__':
    import json

    country_code = 'NL'

    model = GLCModel(country_code='NL')
    model.run()
    raster, meta = model.load_glc_raster_and_meta()

    with rasterio.open(
        f'raster_NL_glc.tif',
        'w',
        driver='GTiff',
        height=raster.shape[0],
        width=raster.shape[1],
        count=1,
        nodata=meta['nodata'],
        dtype=meta['dtype'],
        crs=meta['crs'],
        transform=meta['transform'],
    ) as dst:
        dst.write(raster, 1)
