import netCDF4

import numpy as np

from nansat.exceptions import WrongMapperError
from nansat.vrt import VRT

class Mapper(VRT):

    def __init__(self, filename, gdal_dataset, metadata, *args, **kwargs):

        try:
            ds = netCDF4.Dataset(filename)
        except:
            raise WrongMapperError
        if "title" not in ds.ncattrs():
            raise WrongMapperError
        else:
            if "Surface wind" not in ds.title or "NRCS" not in ds.title:
                raise WrongMapperError
        longitude = ds['longitude'][:].data
        latitude = ds['latitude'][:].data
        for attr in ds.ncattrs():
            content = ds.getncattr(attr)
            #if isinstance(content, str):
            #    content = content.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
            #    content = content.replace("Æ", "Ae").replace("Ø", "Oe").replace("Å", "Aa")
            metadata[attr] = content
        super(Mapper, self)._init_from_lonlat(longitude, latitude)
        
        # Get rid of GDAL additions to metadata keys
        metadata = VRT._remove_strings_in_metadata_keys(metadata, ['NC_GLOBAL#', 'GDAL_'])
        self.dataset.SetMetadata(metadata)
        self.band_vrts = {
            "wind_direction": VRT.from_array(ds["wind_direction"][:].filled(fill_value=np.nan)),
            "look_relative_wind_direction": VRT.from_array(
                ds["look_relative_wind_direction"][:].filled(fill_value=np.nan)),
            "windspeed": VRT.from_array(ds["windspeed"][:].filled(fill_value=np.nan)),
            "model_windspeed": VRT.from_array(ds["model_windspeed"][:].filled(fill_value=np.nan)),
        }
        
        metaDict = []

        wdir_metadict = {}
        for attr in ds["wind_direction"].ncattrs():
            wdir_metadict[attr] = ds["wind_direction"].getncattr(attr)
        metaDict.append({
            'src': {
                'SourceFilename': self.band_vrts["wind_direction"].filename,
                'SourceBand': 1
            },
            'dst': wdir_metadict,
        })
 
        lookrel_metadict = {}
        for attr in ds["look_relative_wind_direction"].ncattrs():
            lookrel_metadict[attr] = ds["look_relative_wind_direction"].getncattr(attr)
        metaDict.append({
            'src': {
                'SourceFilename': self.band_vrts["look_relative_wind_direction"].filename,
                'SourceBand': 1
            },
            'dst': lookrel_metadict,
        })
 
        wspeed_metadict = {}
        for attr in ds["windspeed"].ncattrs():
            wspeed_metadict[attr] = ds["windspeed"].getncattr(attr)
        metaDict.append({
            'src': {
                'SourceFilename': self.band_vrts["windspeed"].filename,
                'SourceBand': 1
            },
            'dst': wspeed_metadict,
        })
 
        mwspeed_metadict = {}
        for attr in ds["model_windspeed"].ncattrs():
            mwspeed_metadict[attr] = ds["model_windspeed"].getncattr(attr)
        metaDict.append({
            'src': {
                'SourceFilename': self.band_vrts["model_windspeed"].filename,
                'SourceBand': 1
            },
            'dst': mwspeed_metadict,
        })
 
        self.create_bands(metaDict)

        self.fix_global_metadata
