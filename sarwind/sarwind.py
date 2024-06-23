""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import os
import pytz
import uuid
import netCDF4
import logging
import datetime

import numpy as np

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
    @classmethod
    def from_wind_nc_product(cls, filename):
        """Initialize SARWind object from an existing CF-NetCDF
        product.
        """
        self = cls.__new__(cls)
        super(SARWind, self).__init__(filename=filename)
        return self

    def __init__(self, sar_image, wind, pixelsize=500, resample_alg=1, max_diff_minutes=30,
                 *args, **kwargs):

        if not isinstance(sar_image, str) or not isinstance(wind, str):
            raise ValueError("Input parameter for SAR and wind direction must be of type string")

        super().__init__(sar_image, *args, **kwargs)

        # If this is a netcdf file with already calculated windspeed
        # do not recalculate wind
        if self.has_band("windspeed"):
            raise ValueError("Wind speed already calculated")

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

        # Get topography
        topo = Nansat(os.getenv("GMTED30"))
        topo.reproject(self, resample_alg=resample_alg, tps=True)
        land = topo[1] > 0
        if land.all():
            raise ValueError("No SAR NRCS ocean coverage.")

        # Set correct time_coverage (opendap mapper sets end=start)
        try:
            ds = netCDF4.Dataset(sar_image)
        except OSError:
            ds = netCDF4.Dataset(sar_image + "#fillmismatch")
        self.set_metadata("time_coverage_start", ds.time_coverage_start)
        self.set_metadata("time_coverage_end", ds.time_coverage_end)

        # Store wind and SAR filenames/urls
        self.set_metadata("wind_filename", wind)
        self.set_metadata("sar_filename", sar_image)

        # Get VV NRCS
        s0vv = self[self.sigma0_bandNo]
        if self.get_metadata(band_id=self.sigma0_bandNo, key="polarization") == "HH":
            inc = self["incidence_angle"]
            # PR from Lin Ren, Jingsong Yang, Alexis Mouche, et al. (2017) [remote sensing]
            PR = np.square(1.+2.*np.square(np.tan(inc*np.pi/180.))) / \
                np.square(1.+1.3*np.square(np.tan(inc*np.pi/180.)))
            s0vv = s0vv*PR

        # Read and reproject model wind field
        aux = Nansat(wind,
                     netcdf_dim={
                         # OBS: timezone info is lost by np.datetime64
                         #      - ignore it, since we always operate
                         #        with UTC
                         "time": np.datetime64(self.time_coverage_start)})
        logging.debug("Reproject model wind field to SAR grid")
        aux.reproject(self, resample_alg=resample_alg, tps=True)

        # Calculate mean time of the SAR NRCS grid
        t0 = datetime.datetime.fromisoformat(
            self.get_metadata("time_coverage_start").replace("Z", "+00:00"))
        t1 = datetime.datetime.fromisoformat(
            self.get_metadata("time_coverage_end").replace("Z", "+00:00"))
        sar_mean_time = t0 + (t1 - t0)/2
        if sar_mean_time.tzinfo is None:
            sar_mean_time = pytz.utc.localize(sar_mean_time)

        # Check time difference between SAR and model
        tdiff = np.abs(sar_mean_time - datetime.datetime.fromisoformat(
            aux.get_metadata(band_id=1, key="time")).replace(tzinfo=pytz.timezone("utc")))
        if tdiff.seconds/60 > max_diff_minutes:
            raise ValueError("Time difference between model and SAR wind field is greater "
                             "than %s minutes - wind speed cannot be reliably estimated."
                             % max_diff_minutes)

        if np.isnan(aux[1]).all():
            raise ValueError("Failing reprojection - make sure the "
                             "datasets overlap in the geospatial "
                             "domain.")

        # Get wind speed and direction
        model_wind_speed, wind_from, time = self.get_model_wind_field(aux)

        ## Add longitude and latitude as bands (should not be necessary..)
        #try:
        #    lon_band_no = self.get_band_number({"standard_name": "longitude"})
        #except ValueError:
        #    lon_band_no = None
        #try:
        #    lat_band_no = self.get_band_number({"standard_name": "latitude"})
        #except ValueError:
        #    lat_band_no = None
        #lon, lat = self.get_geolocation_grids()
        #if lon_band_no is None:
        #    self.add_band(
        #        array=lon,
        #        parameters={
        #            "wkv": "longitude",
        #            "name": "longitude",
        #            "units": "degree_east",
        #        })
        #if lat_band_no is None:
        #    self.add_band(
        #        array=lat,
        #        parameters={
        #            "wkv": "latitude",
        #            "name": "latitude",
        #            "units": "degree_north"
        #        })

        # Store model wind direction
        self.add_band(
            array=wind_from,
            parameters={
                "wkv": "wind_from_direction",
                "name": "wind_direction",
                "short_name": "Wind direction",
                "long_name": "Model wind direction",
                "time": time,
            }
        )

        # Store model wind speed
        self.add_band(
            array=model_wind_speed,
            nomem=True,
            parameters={
                "wkv": "wind_speed",
                "name": "model_windspeed",
                "short_name": "Wind speed",
                "long_name": "Model wind speed",
                "time": time,
            }
        )

        logging.info("Calculating SAR wind with CMOD...")

        startTime = datetime.datetime.now()

        look_dir = self[self.get_band_number({"standard_name": "sensor_azimuth_angle"})]
        look_dir[np.isnan(wind_from)] = np.nan
        look_relative_wind_direction = np.mod(wind_from - look_dir, 360.)
        # Store look relative wind direction
        self.add_band(
            array=look_relative_wind_direction,
            nomem=True,
            parameters={
                "name": "look_relative_wind_direction",
                "units": "degrees",
                "long_name": "Look relative wind direction",
            })

        # Calculate wind speed
        windspeed = cmod5n_inverse(s0vv, look_relative_wind_direction,
                                   self["incidence_angle"])

        logging.info("Calculation time: " + str(datetime.datetime.now() - startTime))

        windspeed[np.where(np.isinf(windspeed))] = np.nan

        # Mask land
        windspeed[topo[1] > 0] = np.nan

        # Add wind speed and direction as bands
        self.add_band(
            array=windspeed,
            parameters={
                "wkv": "wind_speed",
                "name": "windspeed",
                "long_name": "CMOD5n wind speed",
                "short_name": "Wind speed",
                "time": sar_mean_time.isoformat(),
            })

        u = -windspeed*np.sin(wind_from * np.pi / 180.0)
        v = -windspeed*np.cos(wind_from * np.pi / 180.0)
        self.add_band(
            array=u,
            parameters={
                "wkv": "eastward_wind",
                "time": sar_mean_time.isoformat(),
            })
        self.add_band(
            array=v,
            parameters={
                "wkv": "northward_wind",
                "time": sar_mean_time.isoformat(),
            })

        # Update metadata
        metadata = self.get_metadata()
        # When https://github.com/metno/mmd/issues/119 is resolved, update and uncomment:
        # auxm = aux.get_metadata()
        # self.set_related_dataset(metadata, auxm)

        history = metadata.get("history", "")
        self.set_metadata("swhistory", history + "\n%s: %s(%s, %s)" % (
            datetime.datetime.utcnow().replace(tzinfo=pytz.timezone("utc")).isoformat(),
            "SARWind",
            self.get_metadata("wind_filename"),
            self.get_metadata("sar_filename"))
        )

    def set_related_dataset(self, metadata, auxm):
        """Set MMD metadata extension to ACDD. The use of this is
        still unclear and may be changed.

        See https://github.com/metno/mmd/issues/119
        """
        related_dataset = ""
        if "id" in metadata.keys() and "naming_authority" in metadata.keys():
            related_dataset += "%s:%s (auxiliary)" % (metadata.get("naming_authority", ""),
                                                      metadata.get("id", ""))
        elif "id" in metadata.keys() and "naming_authority" not in metadata.keys():
            related_dataset += "%s (auxiliary)" % metadata.get("id", "")

        if related_dataset != "":
            related_dataset += ", "

        if "id" in auxm.keys() and "naming_authority" in auxm.keys():
            related_dataset += "%s:%s (auxiliary)" % (auxm.get("naming_authority", ""),
                                                      auxm.get("id", ""))
        elif "id" in auxm.keys() and "naming_authority" not in auxm.keys():
            related_dataset += "%s (auxiliary)" % auxm.get("id", "")

        if related_dataset.endswith(", "):
            related_dataset = related_dataset[:-2]

        if related_dataset != "":
            self.set_metadata("related_dataset", related_dataset)

        return related_dataset

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
            time = aux.get_metadata(band_id=dir_from_band_no, key="time")
            wind_from = aux[dir_from_band_no]
            speed_band_no = aux.get_band_number({"standard_name": "wind_speed"})
            model_wind_speed = aux[speed_band_no]

        if calc_wind_from:
            title = aux.get_metadata("title")
            # Custom functions are needed here..
            if "arome" in title.lower():
                model_wind_speed, wind_from, time = SARWind.get_arome_arctic_wind(aux)

        return model_wind_speed, wind_from, time

    @staticmethod
    def get_arome_arctic_wind(aux):
        """ Calculate wind_from direction and wind speed from
        Arome-Arctic datasets with erroneous standard names.
        """
        # Make sure that we're dealing with the correct exception
        assert aux.get_metadata("long_name", "y_wind_10m") == "Meridional 10 metre wind (V10M)"
        u = aux["x_wind_10m"]
        v = aux["y_wind_10m"]
        time = aux.get_metadata(band_id="x_wind_10m", key="time")
        speed = np.sqrt(np.square(u) + np.square(v))
        dir = SARWind.calculate_wind_from_direction(u, v)
        return speed, dir, time

    @staticmethod
    def calculate_wind_from_direction(u, v):
        """ Calculate the wind from direction.
        """
        return np.mod(180. + np.arctan2(u, v) * 180./np.pi, 360)

    def export(self, filename=None, bands=None, metadata=None, to_thredds=False, *args, **kwargs):
        """ Export dataset with only wind data to NetCDF-CF, and add
        custom metadata.
        """
        if metadata is None:
            # Necessary to avoid problems when export2thredds calls
            # export..
            super().export(filename, bands=bands, *args, **kwargs)
            return

        if filename is None:
            filename = self.filename.split("/")[-1].split(".")[0] + "_wind.nc"

        if bands is None:
            bands = [
                self.get_band_number("wind_direction"),
                self.get_band_number("look_relative_wind_direction"),
                self.get_band_number("windspeed"),
                self.get_band_number("model_windspeed"),
            ]
            if not to_thredds:
                if bool(self.has_band("longitude")):
                    bands.append(self.get_band_number("longitude"))
                if bool(self.has_band("latitude")):
                    bands.append(self.get_band_number("latitude"))

        swath_mask_band = "swathmask"
        if self.has_band(swathmask_band):
            bands.append(self.get_band_number(swathmask_band)

        metadata = self.set_get_standard_metadata(new_metadata=metadata.copy())

        # Export with Nansat
        if to_thredds:
            bands_dict = {}
            for band in bands:
                mm = self.get_metadata(band_id=band)
                mm.pop("SourceBand", "")
                mm.pop("SourceFilename", "")
                mm.pop("wkv", "")
                mm["dataType"] = 6
                name = mm.pop("name")
                bands_dict[name] = mm
            bands_dict["windspeed"]["colormap"] = "cmocean.cm.speed"
            bands_dict["model_windspeed"]["colormap"] = "cmocean.cm.speed"
            bands_dict["wind_direction"]["colormap"] = "cmocean.cm.phase"
            bands_dict["look_relative_wind_direction"]["colormap"] = "cmocean.cm.phase"
            super().export2thredds(filename, bands=bands_dict,
                                   time=datetime.datetime.fromisoformat(
                                       metadata["time_coverage_start"]))
        else:
            super().export(filename, bands=bands, add_geolocation=False, add_gcps=False, *args,
                           **kwargs)

        # Pop empty metadata
        pop_keys = []
        for key, val in metadata.items():
            if val == "":
                pop_keys.append(key)
        for key in pop_keys:
            metadata.pop(key)

        # Set metadata from dict
        nc_ds = netCDF4.Dataset(filename, "a")
        if metadata is not None:
            for att in nc_ds.ncattrs():
                nc_ds.delncattr(att)
            nc_ds.setncatts(metadata)

        # Clean variable metadata
        md_rm = ["dataType", "SourceBand", "SourceFilename", "wkv", "PixelFunctionType"]
        for key in nc_ds.variables.keys():
            for md_key in md_rm:
                if md_key in nc_ds[key].ncattrs():
                    nc_ds[key].delncattr(md_key)

        # Remove wrong metadata
        sn = "standard_name"
        if swath_mask_band in nc_ds.ncattrs():
            if sn in nc_ds[swath_mask_band].ncattrs():
                nc_ds["swathmask"].delncattr(sn)

        nc_ds.close()

    def to_model_projection(self):
        """Reproject SAR wind field dataset to model grid mapping.
        """
        lon, lat = self.get_corners()
        model = Nansat(self.get_metadata("wind_filename"))
        model.crop_lonlat([lon.min(), lon.max()], [lat.min(), lat.max()])
        model.resize(pixelsize=np.round(
            (self.get_pixelsize_meters()[0]+self.get_pixelsize_meters()[1])/2.), resample_alg=0)
        metadata = self.get_metadata()
        self.vrt.dataset.SetMetadata({})
        self.reproject(model)
        # Update history
        time = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone("utc")).isoformat()
        new_proj = model.get_metadata(band_id=model.get_band_number(
            {"standard_name": "wind_speed"}))["grid_mapping"]
        metadata["history"] = metadata["history"] + \
            "\n{:s}: reproject to {:s} grid mapping".format(time, new_proj)
        self.vrt.dataset.SetMetadata(metadata)

    def set_get_standard_metadata(self, new_metadata=None):
        """Set standard CF and ACDD metadata with MET Norway
        extensions in a dictionary. Replace by values provided in
        new_metadata, if provided. Return the new dictionary.
        """
        if new_metadata is None:
            new_metadata = {}
        # Get metadata
        old_metadata = self.get_metadata()

        if len(old_metadata.keys()) == 1:
            return old_metadata

        t0 = datetime.datetime.fromisoformat(
            old_metadata["time_coverage_start"].replace("Z", "+00:00")
        ).replace(tzinfo=pytz.timezone("utc"))
        t0iso = t0.isoformat()
        t1 = datetime.datetime.fromisoformat(
            old_metadata["time_coverage_end"].replace("Z", "+00:00")
        ).replace(tzinfo=pytz.timezone("utc"))
        t1iso = t1.isoformat()

        sar_filename = old_metadata["sar_filename"].split("/")[-1]
        platforms = {
            "S1A": ["Sentinel-1A", "SAR-C"],
            "S1B": ["Sentinel-1B", "SAR-C"],
        }

        def check_replace(key, in_dict, default_value):
            """Check if key is in in_dict. Return its value if it is
            there, otherwise return the provided default value.
            """
            if key in in_dict:
                return in_dict[key]
            else:
                return default_value

        # Get image boundary
        lon, lat = self.get_border()
        boundary = "POLYGON (("
        for la, lo in list(zip(lat, lon)):
            boundary += "%.2f %.2f, " % (la, lo)
        boundary = boundary[:-2]+"))"

        """Set global CF metadata.
        """
        metadata = {}
        # This can be changed by the user:
        conv = "Conventions"
        metadata[conv] = check_replace(conv, new_metadata, "CF-1.10, ACDD-1.3")
        hist = "history"
        old_hist = old_metadata.pop("swhistory", old_metadata.pop("history"))
        metadata[hist] = check_replace(hist, new_metadata, old_hist)

        """Set global ACDD metadata.
        """
        # This is not negotiable:
        metadata["time_coverage_start"] = t0iso
        metadata["time_coverage_end"] = t1iso
        metadata["geospatial_lat_max"] = "%.2f" % lat.max()
        metadata["geospatial_lat_min"] = "%.2f" % lat.min()
        metadata["geospatial_lon_max"] = "%.2f" % lon.max()
        metadata["geospatial_lon_min"] = "%.2f" % lon.min()
        metadata["geospatial_bounds"] = boundary
        metadata["platform"] = platforms[sar_filename[:3]][0]
        metadata["platform_vocabulary"] = "https://vocab.met.no/mmd/Platform/Sentinel-1A"
        metadata["instrument"] = platforms[sar_filename[:3]][1]
        metadata["instrument_vocabulary"] = "https://vocab.met.no/mmd/Instrument/SAR-C"
        metadata["source"] = "Space Borne Instrument"
        metadata["spatial_representation"] = "grid"
        metadata["wind_filename"] = old_metadata["wind_filename"]
        metadata["sar_filename"] = old_metadata["sar_filename"]
        metadata["iso_topic_category"] = "climatologyMeteorologyAtmosphere"
        if "related_dataset" in old_metadata.keys():
            metadata["related_dataset"] = old_metadata["related_dataset"]

        # This can be changed by the user:
        id = "id"
        metadata[id] = check_replace(id, new_metadata, str(uuid.uuid4()))
        date_created = "date_created"
        metadata[date_created] = check_replace(
            date_created, new_metadata,
            datetime.datetime.utcnow().replace(tzinfo=pytz.timezone("utc")).isoformat())
        title = "title"
        metadata[title] = check_replace(
            title, new_metadata, "Sea surface wind (10 m above sea "
            "level) estimated from {:s} NRCS, acquired on {:s}".format(
                platforms[sar_filename[:3]][0], t0.strftime("%Y-%m-%d %H:%M:%S UTC")))
        title_no = "title_no"
        metadata[title_no] = check_replace(
            title_no, new_metadata, "Overflatevind (10 moh) utledet"
            " fra {:s} NRCS {:s}".format(platforms[sar_filename[:3]][0],
                                         t0.strftime("%Y-%m-%d %H:%M:%S UTC")))
        summary = "summary"
        metadata[summary] = check_replace(
            summary, new_metadata, "Surface wind speed (10 m above "
            "sea level) calculated from C-band Synthetic Aperture Radar (SAR) Normalized Radar "
            "Cross Section (NRCS) and model forecast wind, using CMOD5n. The wind speed is "
            "calculated for neutrally stable conditions and is equivalent to the wind stress.")
        summary_no = "summary_no"
        metadata[summary_no] = check_replace(
            summary_no, new_metadata, "Overflatevind (10 moh) "
            "beregnet fra SAR C-bånd tilbakespredning og vindretning fra varslingsmodell, ved "
            "bruk av CMOD5n. Vindhastigheten er beregnet under antagelse av nøytral "
            "atmosfærestabilitet, og er representativ for vindstress.")
        license = "license"
        metadata[license] = check_replace(license, new_metadata,
                                          "https://spdx.org/licenses/CC-BY-4.0 (CC-BY-4.0)")
        kw = "keywords"
        metadata[kw] = check_replace(
            kw, new_metadata,
            "GCMDSK:EARTH SCIENCE > OCEANS > OCEAN WINDS > SURFACE WINDS > WIND SPEED, "
            "GCMDSK:EARTH SCIENCE > OCEANS > OCEAN WINDS > WIND STRESS, "
            "GEMET:Atmospheric conditions, "
            "NORTHEMES:Vær og klima")
        kw_voc = "keywords_vocabulary"
        metadata[kw_voc] = check_replace(
            kw_voc, new_metadata,
            "GCMDSK:GCMD Science Keywords:https://vocab.met.no/GCMDSK, "
            "GEMET:INSPIRE Themes:http://inspire.ec.europa.eu/theme, "
            "NORTHEMES:GeoNorge Themes:https://register.geonorge.no/metadata-kodelister/"
            "nasjonal-temainndeling")
        refs = "references"
        metadata[refs] = check_replace(refs, new_metadata,
                                       "https://doi.org/10.1029/2006JC003743 (Scientific "
                                       "publication)")
        proc_level = "processing_level"
        metadata[proc_level] = check_replace(proc_level, new_metadata, "Operational")

        nauth = "naming_authority"
        metadata[nauth] = check_replace(nauth, new_metadata, "no.met")
        ptype = "publisher_type"
        metadata[ptype] = check_replace(ptype, new_metadata, "institution")
        pmail = "publisher_email"
        metadata[pmail] = check_replace(pmail, new_metadata, "data-management-group@met.no")

        publ_url = "publisher_url"
        metadata[publ_url] = check_replace(publ_url, new_metadata, "https://www.met.no/")
        publ_name = "publisher_name"
        metadata[publ_name] = check_replace(publ_name, new_metadata,
                                            "Norwegian Meteorological Institute")
        insti = "institution"
        metadata[insti] = check_replace(insti, new_metadata,
                                        "Norwegian Meteorological Institute (MET Norway)")
        access_const = "access_constraint"
        metadata[access_const] = check_replace(access_const, new_metadata, "Open")
        ds_prod_stat = "dataset_production_status"
        metadata[ds_prod_stat] = check_replace(ds_prod_stat, new_metadata, "Complete")
        proj = "project"
        metadata[proj] = check_replace(proj, new_metadata,
                                       "Svalbard Integrated Arctic Earth Observing System – "
                                       "Infrastructure development of the Norwegian node "
                                       "(SIOS-InfraNor)")
        qual = "quality_control"
        metadata[qual] = check_replace(qual, new_metadata, "No quality control")

        # This must be provided as input
        metadata["creator_type"] = new_metadata.pop("creator_type", "")
        metadata["creator_name"] = new_metadata.pop("creator_name", "")
        metadata["creator_email"] = new_metadata.pop("creator_email", "")
        metadata["creator_institution"] = new_metadata.pop("creator_institution", "")
        metadata["contributor_name"] = new_metadata.pop("contributor_name", "")
        metadata["contributor_role"] = new_metadata.pop("contributor_role", "")
        metadata["contributor_email"] = new_metadata.pop("contributor_email", "")
        metadata["contributor_institution"] = new_metadata.pop("contributor_institution", "")

        # Remove filename metadata
        metadata.pop("filename", "")

        return metadata
