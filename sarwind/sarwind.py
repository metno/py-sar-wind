""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import os
import pytz
import uuid
import netCDF4
import logging

import numpy as np

from datetime import datetime

from nansat.nansat import Nansat

from sarwind.cmod5n import cmod5n_inverse


class TimeDiffError(Exception):
    pass


class SARWind(Nansat, object):
    """
    A class for calculating wind speed from SAR images using CMOD.

    Parameters
    -----------
    sar_image : string
        The SAR image as a filename
    wind : string
        Filename of wind field dataset. This must be possible to open with Nansat.
    pixelsize : float or int
        Grid pixel size in metres (0 for full resolution).
    resample_alg : int
        Resampling algorithm used for reprojecting the wind field to
        the SAR image. See nansat.nansat.reproject.
    """

    def __init__(self, sar_image, wind, pixelsize=500, resample_alg=1, *args, **kwargs):

        if not isinstance(sar_image, str) or not isinstance(wind, str):
            raise ValueError("Input parameter for SAR and wind direction must be of type string")

        super().__init__(sar_image, *args, **kwargs)

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
        if self.get_metadata(band_id=self.sigma0_bandNo, key="polarization") == "HH":
            inc = self["incidence_angle"]
            # PR from Lin Ren, Jingsong Yang, Alexis Mouche, et al. (2017) [remote sensing]
            PR = np.square(1.+2.*np.square(np.tan(inc*np.pi/180.))) / \
                np.square(1.+1.3*np.square(np.tan(inc*np.pi/180.)))
            s0hh_band_no = self.get_band_number({
                "standard_name": "surface_backwards_scattering_coefficient_of_radar_wave",
                "polarization": "HH",
                "dataType": "6"
            })
            s0vv = self[s0hh_band_no]*PR

        # Read and reproject model wind field
        aux = Nansat(wind, netcdf_dim={"time": np.datetime64(self.time_coverage_start)})
        aux.reproject(self, resample_alg=resample_alg, tps=True)

        if np.isnan(aux[1]).all():
            raise ValueError("Failing reprojection - make sure the "
                             "datasets overlap in the geospatial "
                             "domain.")

        # We should also get the correct time but this is a bit
        # tricky and requires customization of nansat..

        # Get wind speed and direction
        model_wind_speed, wind_from = self.get_model_wind_field(aux)

        # Store model wind direction
        self.add_band(
            array=wind_from,
            parameters={"wkv": "wind_from_direction", "name": "wind_from_direction"})
        # , "time": wdir_time})

        # Store model wind speed
        self.add_band(
            array=model_wind_speed,
            nomem=True,
            parameters={"wkv": "wind_speed", "name": "model_windspeed"})
        # , "time": wdir_time})

        logging.info("Calculating SAR wind with CMOD...")

        startTime = datetime.now()

        look_dir = self[self.get_band_number({"standard_name": "sensor_azimuth_angle"})]
        look_dir[np.isnan(wind_from)] = np.nan
        look_relative_wind_direction = np.mod(wind_from - look_dir, 360.)

        # Calculate wind speed
        windspeed = cmod5n_inverse(s0vv, look_relative_wind_direction,
                                   self["incidence_angle"])

        logging.info("Calculation time: " + str(datetime.now() - startTime))

        windspeed[np.where(np.isinf(windspeed))] = np.nan

        # Mask land
        topo = Nansat(os.getenv("GMTED30"))
        topo.reproject(self, resample_alg=resample_alg, tps=True)
        windspeed[topo[1] > 0] = np.nan

        # Add wind speed and direction as bands
        # wind_direction_time = self.get_metadata(key="time", band_id="wind_from_direction")
        self.add_band(
            array=windspeed,
            parameters={
                "wkv": "wind_speed",
                "name": "windspeed",
                # "wind_direction_time": wind_direction_time
            })

        u = -windspeed*np.sin(wind_from * np.pi / 180.0)
        v = -windspeed*np.cos(wind_from * np.pi / 180.0)
        self.add_band(array=u, parameters={"wkv": "eastward_wind"})
        self.add_band(array=v, parameters={"wkv": "northward_wind"})

        # set winddir_time to global metadata
        # self.set_metadata("winddir_time", str(wind_direction_time))

        # Update history
        metadata = self.get_metadata()
        history = metadata.get("history", "")
        self.set_metadata("history", history + "%s: %s(%s, %s)" % (
            datetime.now(tz=pytz.UTC).isoformat(),
            "SARWind",
            self.get_metadata("wind_filename"),
            self.get_metadata("sar_filename"))
        )

    @staticmethod
    def get_model_wind_field(aux):
        """ Get model wind speed and direction. This may have to be
        calculated from u and v components.

        Note: old Arome-Arctic datasets did not provide
        wind_from_direction, and used wrong standard names (x_wind
        and y_wind) for the zonal and meridional components.
        """
        calc_wind_from = False
        try:
            dir_from_band_no = aux.get_band_number({"standard_name": "wind_from_direction"})
        except ValueError:
            calc_wind_from = True
        else:
            speed_band_no = aux.get_band_number({"standard_name": "wind_speed"})
            wind_from = aux[dir_from_band_no]
            model_wind_speed = aux[speed_band_no]

        if calc_wind_from:
            title = aux.get_metadata("title")
            # Custom functions are needed here..
            if "arome" in title.lower():
                model_wind_speed, wind_from = SARWind.get_arome_arctic_wind(aux)

        return model_wind_speed, wind_from

    @staticmethod
    def get_arome_arctic_wind(aux):
        """ Calculate wind_from direction and wind speed from
        Arome-Arctic datasets with erroneous standard names.
        """
        # Make sure that we're dealing with the correct exception
        assert aux.get_metadata("long_name", "y_wind_10m") == "Meridional 10 metre wind (V10M)"
        u = aux["x_wind_10m"]
        v = aux["y_wind_10m"]
        speed = np.sqrt(np.square(u) + np.square(v))
        dir = SARWind.calculate_wind_from_direction(u, v)
        return speed, dir

    @staticmethod
    def calculate_wind_from_direction(u, v):
        """ Calculate the wind from direction.
        """
        return np.mod(180. + np.arctan2(u, v) * 180./np.pi, 360)

    def export(self, bands=None, history_message="", *args, **kwargs):
        """ Export dataset to NetCDF-CF and add metadata.
        """
        if "filename" not in kwargs.keys():
            filename = self.filename.split("/")[-1].split(".")[0] + "_wind.nc"
            kwargs["filename"] = filename
        else:
            filename = kwargs["filename"]

        bands = kwargs.pop("bands", None)
        if bands is None:
            bands = [self.get_band_number("wind_from_direction"),
                     self.get_band_number("windspeed"),
                     self.get_band_number("model_windspeed"),
                     # TODO: use standard names:
                     self.get_band_number("U"),
                     self.get_band_number("V"),]

        # TODO: add dataset metadata_id of original file to metadata

        # Export with Nansat
        super().export(bands=bands, *args, **kwargs)

        # Get metadata
        metadata = self.get_metadata()

        # Set dataset id - this is now a new dataset
        metadata["id"] = str(uuid.uuid4())

        # Set global metadata
        sar_filename = metadata["sar_filename"].split("/")[-1]
        platforms = {
            "S1A": ["Sentinel-1A", "SAR-C"],
            "S1B": ["Sentinel-1B", "SAR-C"],
        }
        metadata["title"] = "Surface wind estimated from %s NRCS" % sar_filename
        metadata["title_no"] = "Overflate vind utledet fra %s NRCS" % sar_filename
        metadata["creator_role"] = "Technical contact"
        metadata["creator_type"] = "person"
        metadata["creator_name"] = "Morten Wergeland Hansen"
        metadata["creator_email"] = "mortenwh@met.no"
        metadata["creator_institution"] = "Norwegian Meteorological Institute (MET Norway)"
        metadata["contributor_name"] = "Frode Dinessen"
        metadata["contributor_role"] = "Metadata author"
        metadata["contributor_email"] = "froded@met.no"
        metadata["contributor_institution"] = "Norwegian Meteorological Institute (MET Norway)"
        metadata["project"] = "MET Norway core services (METNCS)"
        metadata["institution"] = "Norwegian Meteorological Institute (MET Norway)"
        metadata["publisher_type"] = "institution"
        metadata["publisher_name"] = "Norwegian Meteorological Institute"
        metadata["publisher_url"] = "https://www.met.no/"
        metadata["publisher_email"] = "data-management-group@met.no"
        metadata["references"] = "https://doi.org/10.1029/2006JC003743 (Scientific publication)"
        metadata["dataset_production_status"] = "Complete"
        metadata["summary"] = ("Wind speed calculated from C-band Synthetic"
                               " Aperture Radar (SAR) Normalized Radar Cross Section (NRCS)"
                               " and model forecast wind, using CMOD5n. The wind speed is "
                               "calculated for neutrally stable conditions and is, as such, "
                               "equivalent to the wind stress.")
        metadata["summary_no"] = ("Vindstyrke beregnet fra SAR C-bånd tilbakespredning og "
                                  "vindretning fra varslingsmodell, ved bruk av CMOD5n. "
                                  "Vindstyrken er beregnet under antagelse av nøytral "
                                  "atmosfærestabilitet, og er dermed representativ for "
                                  "vindstress.")
        metadata["platform"] = platforms[sar_filename[:3]][0]
        metadata["platform_vocabulary"] = "https://vocab.met.no/mmd/Platform/Sentinel-1A"
        metadata["instrument"] = platforms[sar_filename[:3]][1]
        metadata["instrument_vocabulary"] = "https://vocab.met.no/mmd/Instrument/SAR-C"
        metadata["Conventions"] = "CF-1.10, ACDD-1.3"
        metadata["keywords"] = (
            "GCMDSK: EARTH SCIENCE > OCEANS > OCEAN WINDS > SURFACE WINDS > WIND SPEED, "
            "GCMDSK: EARTH SCIENCE > OCEANS > OCEAN WINDS > WIND STRESS, "
            "GEMET: Atmospheric conditions, "
            "NORTHEMES: Vær og klima")
        metadata["keywords_vocabulary"] = (
            "GCMDSK:GCMD Science Keywords:https://vocab.met.no/GCMDSK, "
            "GEMET:INSPIRE Themes:http://inspire.ec.europa.eu/theme, "
            "NORTHEMES:GeoNorge Themes:https://register.geonorge.no/metadata-kodelister/"
            "nasjonal-temainndeling")

        # Get image boundary
        lon, lat = self.get_border()
        boundary = "POLYGON (("
        for la, lo in list(zip(lat, lon)):
            boundary += "%.2f %.2f, "%(la, lo)
        boundary = boundary[:-2]+"))"
        # Set bounds as (lat,lon) following ACDD convention and EPSG:4326
        metadata["geospatial_bounds"] = boundary
        metadata["geospatial_bounds_crs"] = "EPSG:4326"

        metadata["sar_wind_resource"] = \
            "https://github.com/metno/met-sar-vind"

        # Set metadata from dict
        ncid = netCDF4.Dataset(filename, "a")
        ncid.setncatts(metadata)
        ncid.close()
