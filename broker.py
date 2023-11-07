""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
from datetime import datetime, timedelta
from sardata.sardataNBS import SARData
from sarwind.sarwind import SARWind
from winddata.winddata import WINDdata
import warnings
import pytz
import os
import fnmatch
from nansat.nansat import Nansat
import subprocess

os.environ.setdefault('GDAL_ENABLE_DEPRECATED_DRIVER_DODS','YES')


class Broker():
    """
     This class search for Sentinel-1 data from NBS and Arome-Arctic wind data
     from thredds.
     If matching data is found processing of SAR-wind is started.

     Parameters
     -----------
     endpoint : str
               URL to Data. Default: https://csw.s-enda-dev.k8s.met.no/csw

     bbox     : int list
               A boudary box for search area speified in latitude and longitude
               bbox = [lon_min, lat_min, lon_max, lat_max]

               Example:
               >>> bbox = [-10, 75, 40, 85]

     start    : datetime object
               Specify the start time of the range to serchthe

     stop     :  datetime object
               Specify the stop time of the range to search

               Example:
               >>> from datetime import datetime, timedelta
               >>> stop = datetime(2010, 1, 1, 12, 30, 59).replace(tzinfo=pytz.utc)
               >>> start = stop - timedelta(days=7)

     kw_names : str
               A search string filter to limit the result of a search.
               Example:
               >>> kw_name='Arome-Arctic%'
    """

    def __init__(self, bbox=[-25, 60, 70, 85], start=None, stop=None):
        # Set start and stop value to today if not provided as argument
        if not isinstance(start, datetime) or not isinstance(stop, datetime):
            warnings.warn('Start/stop time not provided. Using current time as default!')
            start = datetime.now().replace(tzinfo=pytz.utc)
            stop = start + timedelta(days=1)
        print('\nSearch for new Sentinel-1 data between start: %s stop: %s' % (start.strftime('%Y%m%dT%H'), stop.strftime('%Y%m%dT%H')))
        self.start = start
        self.stop = stop
        self.outpath = '/data/sar_wind_products/%04d/%02d/' % (start.year,start.month)
        if not os.path.exists(self.outpath):
            os.makedirs(self.outpath)

        self.sw_filenames = []
        self.nc_filenames = []

        # Find available Sentinel-1 data in NBS
        self.sar_freetext = '%1A_EW%'
        self.model_freetext = 'Arome-Arctic%'
        self.bbox = bbox
        self.wind = ''
        self.main()

    def main(self):
        #  Search NBS for Sentinel-1 data
        #  NB! currently no check if data has alredy been processed.
        sar = SARData(start=self.start, stop=self.stop, bbox=self.bbox, kw_names=self.sar_freetext)
        # print(sar.url_opendap)

        if len(sar.url_opendap) == 0:
            raise Exception('No SAR data available for the requested date/time')

        # Get Arome Arctic data and start the wind generateion
        for sarfile in sar.url_opendap:
            # Check if already processed by looking in the output path
            if (len(self._find_files('%s*' % (os.path.basename(sarfile).split('.')[0]))) > 0):
                print('Already processed: %s' % sarfile)
                continue
            
            # Looking for model wind data
            try:
                modelUrl = self._get_arome_file(sarfile, self.bbox)
            except Exception as e:
                print(e)
                modelUrl = ''
                print('Not able to find arome data matching %s' % (sarfile))
                continue

            # Start running CMOD wind processing
            print('Start processing on:')
            print('SAR file: %s' % sarfile)
            print('Model file: %s' % modelUrl)
            try:
                sw = SARWind(sarfile, modelUrl)
                ncfilename = '%s/%s_wind.nc' % (self.outpath, os.path.basename(sarfile).split('.')[0])
                sw.export(ncfilename, bands=[22, 23, 24, 25])
                # sw.plot()
                self.sw_filenames.append(sarfile)
                self.nc_filenames.append(ncfilename)
                
                dstpath = '/lustre/storeB/project/fou/fd/project/sar-wind/products/%04d/%02d/%02d' % (self.start.year,self.start.month, self.start.day)
                cmd = 'ssh -i /home/ubuntu/.ssh/id_rsa \"froded@ppi-clogin-a1.met.no\" \"mkdir -p %s\"' % dstpath
                print(cmd)
                subprocess.call(cmd, shell=True)


                cmd = 'scp -i /home/ubuntu/.ssh/id_rsa %s froded@ppi-clogin-a1.met.no:%s/' % (ncfilename, dstpath)
                print(cmd)
                subprocess.call(cmd, shell=True)

            except:
                print('Could not generate wind from files')
                print('SAR file: %s' % sarfile)
                print('Arome file: %s' % modelUrl) 
         
        # TODO: Keep track of processed files. 
        # For now I am only checking for filename in output netCDF path.
        # Processed files are available from self.nc_filenames

    def _getURL(self, seachStr, url_opendap):
        modelUrl = ''
        for m in url_opendap:
            if (m.find(seachStr) > -1):
                modelUrl = m
        return modelUrl

    def _get_arome_time(self, hour):
        # Get closest %3 hours back in time from input hours
        hour = int(hour)
        if hour%3 == 2:
            time_closest = '%02d' % (hour + (3-hour%3))
        else:
            time_closest = '%02d' % (hour - hour%3)
        return time_closest

    def _get_arome_file(self, sarfile, bbox):
        nobject = Nansat(sarfile)
        ntime = nobject.time_coverage_end
        hour = self._get_arome_time(ntime.hour)

        # Need to search 4 days ahead in time to find match of model wind
        modelstart = datetime(ntime.year, ntime.month, ntime.day,
                              int(hour), 0, 0).replace(tzinfo=pytz.utc)
        modelstop = datetime(ntime.year, ntime.month,
                             (ntime.day+4), 0, 0, 0).replace(tzinfo=pytz.utc)
        print(modelstart, modelstop)

        # Find available NWP model file og continue to next SAR file
        model_freetext = '%Arome-Arctic'
        modelwind = WINDdata(start=modelstart, stop=modelstop, bbox=bbox, kw_names=model_freetext)
        if len(modelwind.url_opendap) == 0:
            raise Exception('No arome data available for date %04d-%02d-%02d' %
                            (modelstart.year, modelstart.month, modelstart.day))

        modelUrl = ''
        cnt = 0
        while ((modelUrl == '') and (cnt < 3)):
            previous_time = ((datetime(modelstart.year, modelstart.month, modelstart.day,
                                       modelstart.hour))-\
                             timedelta(hours=cnt*3)).replace(tzinfo=pytz.utc)
            seachStr = 'arome_arctic_det_2_5km_%04d%02d%02dT%02d' % (previous_time.year,
                                                                     previous_time.month,
                                                                     previous_time.day,
                                                                     previous_time.hour)
            modelUrl = self._getURL(seachStr, modelwind.url_opendap)
            cnt += 1
        return modelUrl

    def _find_files(self, pattern):
        '''Return list of files matching pattern in self.outpath folder.'''
        return [n for n in fnmatch.filter(os.listdir(self.outpath), pattern) if
            os.path.isfile(os.path.join(self.outpath, n))]


if __name__ == '__main__':
    #start = datetime(2023, 10, 6, 0, 0, 0).replace(tzinfo=pytz.utc)
    #stop = datetime(2023, 10, 7, 0, 0, 0).replace(tzinfo=pytz.utc)

    now  = datetime.now().replace(tzinfo=pytz.utc)
    start = datetime(now.year, now.month, now.day, 0, 0, 0).replace(tzinfo=pytz.utc)
    stop = start + timedelta(days=1)

    broker_object = Broker(start=start, stop=stop)
    # broker_object.wind.plot()  
