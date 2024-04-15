""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import os
import warnings
import logging
import pytz
from datetime import datetime
from dateutil.parser import parse
import numpy as np
from nansat.nansat import Nansat
from sarwind.cmod5n import cmod5n_inverse
from matplotlib import pyplot as plt
from matplotlib import cm
import uuid
import netCDF4


class TimeDiffError(Exception):
    pass


class SARWind(Nansat, object):
    """
    A class for calculating wind speed from SAR images using CMOD

    Parameters
    -----------
    sar_image : string
                The SAR image as a filename
    wind : string
                Filename of wind field dataset. This must be possible to open with Nansat.
    pixelsize : float or int
                Grid pixel size in metres (0 for full resolution)
    resample_alg : int
                Resampling algorithm used for reprojecting wind field
                to SAR image
                    -1 : Average,
                     0 : NearestNeighbour
                     1 : Bilinear (default),
                     2 : Cubic,
                     3 : CubicSpline,
                     4 : Lancoz
    """

    def __init__(self, sar_image, wind, pixelsize=500, resample_alg=1, *args, **kwargs):

        if not isinstance(sar_image, str) or not isinstance(wind, str):
            raise ValueError("Input parameter for SAR and wind direction must be of type string")

        super(SARWind, self).__init__(sar_image, *args, **kwargs)

        self.set_metadata("wind_filename", wind)
        self.set_metadata("sar_filename", sar_image)

        # If this is a netcdf file with already calculated windspeed
        # do not recalculate wind
        if self.has_band("windspeed"):
            raise Exception("Wind speed already calculated")

        # Get HH pol NRCS (since we don't want to use pixel function generated VV pol)
        try:
            self.sigma0_bandNo = self.get_band_number({
                "standard_name":
                    "surface_backwards_scattering_coefficient_of_radar_wave",
                "polarization": "HH",
                "dataType": "6"
            })
        except ValueError:
            self.sigma0_bandNo = self.get_band_number({
                "standard_name":
                    "surface_backwards_scattering_coefficient_of_radar_wave",
                "polarization": "VV",
                "dataType": "6"
            })

        # Resize to given pixel size (default 500 m)
        self.resize(pixelsize=pixelsize)

        # Get VV NRCS
        s0vv = self[self.sigma0_bandNo]
        if self.get_metadata(band_id=self.sigma0_bandNo, key='polarization') == 'HH':
            inc = self['incidence_angle']
            # PR from Lin Ren, Jingsong Yang, Alexis Mouche, et al. (2017) [remote sensing]
            PR = np.square(1.+2.*np.square(np.tan(inc*np.pi/180.))) / \
                np.square(1.+1.3*np.square(np.tan(inc*np.pi/180.)))
            s0hh_band_no = self.get_band_number({
                'standard_name':
                    'surface_backwards_scattering_coefficient_of_radar_wave',
                'polarization': 'HH',
                'dataType': '6'
            })
            s0vv = self[s0hh_band_no]*PR

        # Read and reproject model wind field
        aux = Nansat(wind, netcdf_dim = {"time": np.datetime64(self.time_coverage_start)})
        aux.reproject(self, resample_alg=resample_alg, tps=True)

        # We should also get the correct time but this is a bit
        # tricky and requires customization of nansat..

        # Store model wind direction
        dir_from_band_no = aux.get_band_number({"standard_name": "wind_from_direction"})
        wind_from = aux[dir_from_band_no]
        self.add_band(
            array = wind_from,
            parameters = {'wkv': 'wind_from_direction', 'name': 'wind_from_direction'})
            # , 'time': wdir_time})
        
        # Store model wind speed
        speed_band_no = aux.get_band_number({"standard_name": "wind_speed"})
        self.add_band(
            array = aux[speed_band_no],
            nomem = True,
            parameters = {'wkv': 'wind_speed', 'name': 'model_windspeed'})
        # , 'time': wdir_time})

        logging.info('Calculating SAR wind with CMOD...')

        startTime = datetime.now()

        look_dir = self[self.get_band_number({'standard_name': 'sensor_azimuth_angle'})]
        look_dir[np.isnan(wind_from)] = np.nan
        look_relative_wind_direction = np.mod(wind_from - look_dir, 360.)

        # Calculate wind speed
        windspeed = cmod5n_inverse(s0vv, look_relative_wind_direction,
                                   self['incidence_angle'])

        logging.info('Calculation time: ' + str(datetime.now() - startTime))

        windspeed[np.where(np.isinf(windspeed))] = np.nan

        # Mask land
        topo = Nansat(os.getenv("GMTED30"))
        topo.reproject(self, resample_alg=resample_alg, tps=True)
        windspeed[topo[1] > 0] = np.nan

        # Add wind speed and direction as bands
        # wind_direction_time = self.get_metadata(key='time', band_id='wind_from_direction')
        self.add_band(
            array=windspeed,
            parameters={
                'wkv': 'wind_speed',
                'name': 'windspeed',
                #'wind_direction_time': wind_direction_time
            })

        u = -windspeed*np.sin(wind_from * np.pi / 180.0)
        v = -windspeed*np.cos(wind_from * np.pi / 180.0)
        self.add_band(array=u, parameters={'wkv': 'eastward_wind'})
        self.add_band(array=v, parameters={'wkv': 'northward_wind'})

        # set winddir_time to global metadata
        # self.set_metadata('winddir_time', str(wind_direction_time))

        # Update history
        history = ""
        if "history" in self.vrt.dataset.GetMetadata_List():
            history = self.get_metadata("history")
        self.set_metadata("history", history + "%s: %s(%s, %s)" % (
            datetime.now(tz=pytz.UTC).isoformat(),
            "SARWind",
            self.get_metadata('wind_filename'),
            self.get_metadata('sar_filename'))
        )

    def get_bands_to_export(self, bands):
        if not bands:
            bands = [self.get_band_number('wind_from_direction'),
                     self.get_band_number('windspeed'),
                     self.get_band_number('model_windspeed'),
                     self.get_band_number('U'),
                     self.get_band_number('V'),]
        return bands

    def _export(self, *args, **kwargs):
        bands = kwargs.pop('bands', None)
        # TODO: add name of original file to metadata

        super(SARWind, self).export(bands=self.get_bands_to_export(bands), *args, **kwargs)

    def export2netcdf(self, history_message='', filename='', bands=None):
        if not filename:
            raise ValueError('Please provide a netcdf filename!')

        # Export data to netcdf
        self._export(filename=filename, bands=bands)

        # Get metadata
        metadata = self.get_metadata()

        # Updata history
        try:
            history = metadata['history']
        except ValueError:
            history = ''

        if not history_message:
            history_message = '%s: %s, SARWind.export2netcdf(%s)' % \
                (datetime.now(tz=pytz.UTC).isoformat(), history, filename.split('/')[-1])
        else:
            history_message = '%s: %s, %s' % \
                (datetime.now(tz=pytz.UTC).isoformat(), history, history_message)

        metadata['history'] = history_message

        # Get and set dataset id
        if 'id' not in metadata.keys():
            metadata['id'] = str(uuid.uuid4())

        # Set global metadata
        sar_filename = metadata['sar_filename'].split('/')[-1]
        metadata['title'] = 'Surface wind derived from %s' % sar_filename
        metadata['title_no'] = 'Overflate vind utledet fra %s' % sar_filename
        metadata['creator_role'] = 'Technical contact'
        metadata['creator_type'] = 'person'
        metadata['creator_name'] = 'Morten Wergeland Hansen'
        metadata['creator_email'] = 'mortenwh@met.no'
        metadata['creator_institution'] = 'Norwegian Meteorological Institute (MET Norway)'
        metadata['contributor_name'] = 'Frode Dinessen'
        metadata['contributor_role'] = 'Metadata author'
        metadata['contributor_email'] = 'froded@met.no'
        metadata['contributor_institution'] = 'Norwegian Meteorological Institute (MET Norway)'
        metadata['project'] = 'MET Norway core services (METNCS)'
        metadata['institution'] = 'Norwegian Meteorological Institute (MET NOrway)'
        metadata['publisher_type'] = 'institution'
        metadata['publisher_name'] = 'Norwegian Meteorological Institute'
        metadata['publisher_url'] = 'https://www.met.no/'
        metadata['publisher_email'] = 'csw-services@met.no'
        metadata['references'] = 'https://www.researchgate.net/publication/'\
            '288260682_CMOD5_An_improved_geophysical_model_function_for_ERS_C-band_scatterometry '\
            '(Scientific publication)'
        metadata['doi'] = '10.1029/2006JC003743'
        metadata['dataset_production_status'] = 'Complete'
        metadata['summary'] = 'Derived wind information based on the SENTINEL-1 C-band synthetic' \
            ' aperture radar mission'
        metadata['summary_no'] = 'Beregnet vindstyrkt og vindretning utledet fra SENTINEL-1 '\
            'C-band Synthetic Aperture Radar (SAR) mission'
        metadata['platform'] = 'Sentinel-1%s' % sar_filename[2]
        metadata['platform_vocabulary'] = 'https://vocab.met.no/mmd/Platform/Sentinel-1A'
        metadata['instrument'] = 'SAR-C'
        metadata['instrument_vocabulary'] = 'https://vocab.met.no/mmd/Instrument/SAR-C'
        metadata['Conventions'] = 'CF-1.10,ACDD-1.3'
        metadata['keywords'] = 'GCMDSK:Earth Science > Oceans > RADAR backscatter > Wind'
        metadata['keywords'] = 'GCMDSK:Earth Science > Oceans > RADAR backscatter > '\
            'Wind, GCMDSK:Earth Science > Spectral/Engineering > RADAR > RADAR imagery,'\
            'GCMDLOC:Geographic Region > Northern Hemisphere, GCMDLOC:Vertical Location > '\
            'Sea Surface, GCMDPROV: Government Agencies-non-US > Norway > NO/MET > '\
            'Norwegian Meteorological Institute'
        metadata['keywords_vocabulary'] = 'GCMDSK:GCMD Science Keywords:'\
            'https://gcmd.earthdata.nasa.gov/kms/concepts/concept_scheme/sciencekeywords,'\
            'GCMDPROV:GCMD Providers:https://gcmd.earthdata.nasa.gov/kms/concepts/'\
            'concept_scheme/providers,'\
            'GCMDLOC:GCMD Locations:https://gcmd.earthdata.nasa.gov/kms/concepts/'\
            'concept_scheme/locations'

        # Get image boundary
        lon, lat = self.get_border()
        boundary = 'POLYGON (('
        for la, lo in list(zip(lat, lon)):
            boundary += '%.2f %.2f, '%(la, lo)
        boundary = boundary[:-2]+'))'
        # Set bounds as (lat,lon) following ACDD convention and EPSG:4326
        metadata['geospatial_bounds'] = boundary
        metadata['geospatial_bounds_crs'] = 'EPSG:4326'

        metadata['sar_wind_resource'] = \
            "https://github.com/metno/met-sar-vind"

        # Set metadata from dict
        ncid = netCDF4.Dataset(filename, 'r+')
        ncid.setncatts(metadata)
        ncid.close()
