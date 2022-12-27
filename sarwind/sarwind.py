""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import sys
import argparse
import warnings
from datetime import datetime
from dateutil.parser import parse

import numpy as np

from nansat.nansat import Nansat, Domain, _import_mappers

from sarwind.cmod5n import cmod5n_inverse

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

    def __init__(self, sar_image, wind,
                    pixelsize=500, resample_alg=1, *args, **kwargs):

        if not isinstance(sar_image, str) or not isinstance(wind, str):
            raise ValueError('Input parameter for SAR and wind direction must be of type string')

        super(SARWind, self).__init__(sar_image, *args, **kwargs)

        # If this is a netcdf file with already calculated windspeed
        # do not recalculate wind
        if self.has_band('windspeed'):
            raise Exception('Wind speed already calculated')

        # Get HH pol NRCS (since we don't want to use pixel function generated VV pol)
        try:
            self.sigma0_bandNo = self.get_band_number({
                'standard_name':
                    'surface_backwards_scattering_coefficient_of_radar_wave',
                'polarization': 'HH',
                'dataType': '6'
            })
        except ValueError:
            self.sigma0_bandNo = self.get_band_number({
                'standard_name':
                    'surface_backwards_scattering_coefficient_of_radar_wave',
                'polarization': 'VV',
                'dataType': '6'
            })

        if pixelsize != 0:
            print('Resizing SAR image to ' + str(pixelsize) + ' m pixel size')
            self.resize(pixelsize=pixelsize)

        if not self.has_band('wind_direction'):
            self.set_aux_wind(wind, resample_alg=resample_alg,
                    **kwargs)

        self._calculate_wind()

        # Set watermask
        try:
            valid = self.watermask(tps=True)[1]
        except OSError as e:
            warnings.warn(str(e))
        else:
            valid[valid==2] = 0
            self.add_band(array=valid, parameters={
                            'name': 'valid',
                            'note': 'All pixels not equal to 1 are invalid',
                            'long_name': 'Valid pixels (covering open water)'
                        })


    def set_aux_wind(self, wind, *args, **kwargs):
        """
        Add auxiliary wind direction as a band with source information in the
        global metadata.

        Parameters
        -----------
        wind : string
                    The name of a Nansat compatible file containing wind direction information
        """
        wspeed, wdir, wdir_time = self._get_aux_wind_from_str(wind, *args, **kwargs)


        self.add_band(array=wdir, parameters={
                            'wkv': 'wind_from_direction',
                            'name': 'winddirection',
                            'time': wdir_time
                })
        if not wspeed is None:
            self.add_band(array=wspeed, nomem=True, parameters={
                            'wkv': 'wind_speed',
                            'name': 'model_windspeed',
                            'time': wdir_time,
            })

    def _get_aux_wind_from_str(self, aux_wind_source, *args, **kwargs):
        """ Get wind field from a file (aux_wind_source) that can be
        opened with Nansat.
        """
        import nansat.nansat
        mnames = [key.replace('mapper_','') for key in
                    nansat.nansat.nansatMappers]
        # check if aux_wind_source is like 'ncep_wind_online', i.e. only
        # mapper name is given. By adding the SAR image time stamp, we
        # can then get the data online
        if aux_wind_source in mnames:
            aux_wind_source = aux_wind_source + \
                    datetime.strftime(self.time_coverage_start, ':%Y%m%d%H%M')
        aux = Nansat(aux_wind_source, netcdf_dim={
                'time': np.datetime64(self.time_coverage_start),
                'height2': 10,  # height dimension used in AROME arctic datasets
                'height3': 10,
            },
            bands = [ # CF standard names of desired bands
                'x_wind_10m',
                'y_wind_10m', # or..:
                'x_wind',
                'y_wind', # or..:
                'eastward_wind',
                'northward_wind',
            ])
        # Set filename of source wind in metadata
        try:
            wind_u_bandNo = aux.get_band_number({
                        'standard_name': 'eastward_wind',
                    })
        except ValueError:
            try:
                wind_u_bandNo = aux.get_band_number({
                        'standard_name': 'x_wind',
                    })
            except:
                wind_u_bandNo = aux.get_band_number({
                        'standard_name': 'x_wind_10m',
                    })
        self.set_metadata('WIND_DIRECTION_SOURCE', aux_wind_source)
        wspeed, wdir, wdir_time = self._get_wind_direction_array(aux,
                                        *args, **kwargs)

        return wspeed, wdir, wdir_time

    def _get_wind_direction_array(self, aux_wind, resample_alg=1, *args,
            **kwargs):
        """ Reproject the wind field and return the wind directions,
        time and speed.
        """
        if not isinstance(aux_wind, Nansat):
            raise ValueError('Input parameter must be of type Nansat')

        try:
            eastward_wind_bandNo = aux_wind.get_band_number({
                        'standard_name': 'eastward_wind',
                    })
        except ValueError:
            try:
                x_wind_bandNo = aux_wind.get_band_number({
                        'standard_name': 'x_wind',
                    })
                y_wind_bandNo = aux_wind.get_band_number({
                        'standard_name': 'y_wind',
                    })
            except:
                x_wind_bandNo = aux_wind.get_band_number({
                        'standard_name': 'x_wind_10m',
                    })
                y_wind_bandNo = aux_wind.get_band_number({
                        'standard_name': 'y_wind_10m',
                    })
            # Get azimuth of aux_wind y-axis in radians
            az = aux_wind.azimuth_y()*np.pi/180
            # Get x direction wind
            x_wind = aux_wind[x_wind_bandNo]
            fvx = float(aux_wind.get_metadata(band_id=x_wind_bandNo, key='_FillValue'))
            x_wind[x_wind == fvx] = np.nan
            # Get y direction wind
            y_wind = aux_wind[y_wind_bandNo]
            fvy = float(aux_wind.get_metadata(band_id=y_wind_bandNo, key='_FillValue'))
            y_wind[y_wind == fvy] = np.nan

            # Get east-/westward wind speeds
            uu = y_wind*np.sin(az) + x_wind*np.cos(az)
            vv = y_wind*np.cos(az) - x_wind*np.sin(az)
            # Add bands and override minmax from nersc wkv
            aux_wind.add_band(array=uu, parameters={'wkv': 'eastward_wind', 'minmax': '-25 25'})
            aux_wind.add_band(array=vv, parameters={'wkv': 'northward_wind', 'minmax': '-25 25'})

        ## Crop wind field to SAR image area of coverage (to avoid issue with
        ## polar stereographic data mentioned in nansat.nansat.Nansat.reproject
        ## comments)
        #aux_wind.crop_lonlat([nlonmin, nlonmax], [nlatmin, nlatmax])

        # Then reproject
        aux_wind.reproject(self, resample_alg=resample_alg, tps=True)

        if not 'WIND_DIRECTION_SOURCE' in self.get_metadata().keys():
            self.set_metadata('WIND_DIRECTION_SOURCE', aux_wind.filename)

        # Check time difference between SAR image and wind direction object
        timediff = self.time_coverage_start.replace(tzinfo=None) - \
            parse(aux_wind.get_metadata('time_coverage_start'))

        hoursDiff = np.abs(timediff.total_seconds()/3600.)

        print('Time difference between SAR image and wind direction: %.2f hours' % hoursDiff)
        print('SAR image time: ' + str(self.time_coverage_start))
        print('Wind dir time: ' + str(parse(aux_wind.get_metadata('time_coverage_start'))))
        if hoursDiff > 3:
            warnings.warn('Time difference exceeds 3 hours!')
            if hoursDiff > 12:
                raise TimeDiffError('Time difference is %.f - impossible to '
                                    'estimate reliable wind field' % hoursDiff)

        # Get band numbers of eastward and northward wind
        eastward_wind_bandNo = aux_wind.get_band_number({'standard_name': 'eastward_wind'})
        northward_wind_bandNo = aux_wind.get_band_number({'standard_name': 'northward_wind'})

        # Get mask, and eastward and northward wind speed components
        mask = aux_wind['swathmask']
        uu = aux_wind[eastward_wind_bandNo]
        uu[mask == 0] = np.nan
        vv = aux_wind[northward_wind_bandNo]
        vv[mask == 0] = np.nan

        if uu is None:
            raise Exception('Could not read wind vectors')
        # 0 degrees meaning wind from North, 90 degrees meaning wind from East
        # Return wind direction, time, wind speed
        wind_dir = np.degrees(np.arctan2(-uu, -vv))
        time = aux_wind.time_coverage_start
        wind_speed = np.sqrt(np.power(uu, 2) + np.power(vv, 2))
        return wind_speed, wind_dir, time

    def _calculate_wind(self):
        """ Calculate wind speed from SAR sigma0 in VV polarization.
        """
        # Calculate SAR wind with CMOD
        # TODO:
        # - add other CMOD versions than CMOD5
        print('Calculating SAR wind with CMOD...')
        startTime = datetime.now()
        look_dir = self[self.get_band_number({'standard_name': 'sensor_azimuth_angle'})]

        s0vv = self[self.sigma0_bandNo]

        if self.get_metadata(band_id=self.sigma0_bandNo, key='polarization') == 'HH':
            # This is a hack to use another PR model than in the nansat pixelfunctions
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

        fillval = float(self.get_metadata(band_id=self.sigma0_bandNo, key='_FillValue'))
        s0vv[s0vv == fillval] = np.nan

        winddir = self['winddirection']
        look_dir[np.isnan(winddir)] = np.nan
        look_relative_wind_direction = np.mod(winddir - look_dir, 360.)
        windspeed = cmod5n_inverse(s0vv, look_relative_wind_direction,
                                   self['incidence_angle'])
        print('Calculation time: ' + str(datetime.now() - startTime))

        windspeed[np.where(np.isnan(windspeed))] = np.nan
        windspeed[np.where(np.isinf(windspeed))] = np.nan

        # Add wind speed and direction as bands
        wind_direction_time = self.get_metadata(key='time', band_id='winddirection')
        self.add_band(
            array=windspeed,
            parameters={
                'wkv': 'wind_speed',
                'name': 'windspeed',
                'time': self.time_coverage_start,
                'wind_direction_time': wind_direction_time
            })

        # TODO: Replace U and V bands with pixelfunctions
        u = -windspeed*np.sin((180.0 - self['winddirection'])*np.pi/180.0)
        v = windspeed*np.cos((180.0 - self['winddirection'])*np.pi/180.0)
        self.add_band(array=u, parameters={
                            'wkv': 'eastward_wind',
                            'time': wind_direction_time,
        })
        self.add_band(array=v, parameters={'wkv': 'northward_wind', 'time': wind_direction_time})

        # set winddir_time to global metadata
        self.set_metadata('winddir_time', str(wind_direction_time))

    def get_bands_to_export(self, bands):
        if not bands:
            bands = [
                self.get_band_number('valid'),
                self.get_band_number('winddirection'),
                self.get_band_number('windspeed'),
                self.get_band_number('model_windspeed'),
            ]
        return bands

    def export(self, *args, **kwargs):
        bands = kwargs.pop('bands', None)
        # TODO: add name of original file to metadata

        super(SARWind, self).export(bands=self.get_bands_to_export(bands), *args, **kwargs)
