#!/usr/bin/env python3
"""
Script to reproject SAR wind to forecast model projection

License:

This file is part of the met-sar-vind repository
<https://github.com/metno/met-sar-vind>.

met-sar-vind is licensed under the Apache License 2.0
<https://github.com/metno/met-sar-vind/blob/master/LICENSE>

"""
import os
import pytz
import uuid
import logging
import netCDF4
import datetime
import argparse

import numpy as np

from pathlib import Path

from nansat.nansat import Nansat

from sarwind.script.process_sar_wind import export_mmd


def create_parser():
    parser = argparse.ArgumentParser(
        description="Reproject SAR wind to forecast model grid."
    )
    parser.add_argument(
        "--sarwind", type=str,
        help="SAR wind filename."
    )
    parser.add_argument(
        "-o", "--output_path", type=str, default=".",
        help="Output path of resulting CF-NetCDF file (default is the"
             " current directory)."
    )
    parser.add_argument(
        "--parent_mmd", type=str, default=None,
        help="Metadata ID of parent dataset."
    )
    parser.add_argument(
        "--nc_target_path", type=str, default=".",
        help="Target path for the CF-NetCDF files if they need to be "
             "moved to another storage place than the given output "
             "path (default is the current directory)."
    )
    parser.add_argument(
        "--odap_target_url", type=str, default=None,
        help="Root folder of the OPeNDAP target url."
    )

    return parser


def main(args=None):
    """Reproject and export SAR wind to a new dataset.
    """
    n = Nansat(args.sarwind, mapper="sarwind")
    model = Nansat(n.get_metadata("wind_filename"))
    lon, lat = n.get_corners()
    model.crop_lonlat([lon.min(), lon.max()], [lat.min(), lat.max()])
    model.resize(pixelsize=np.round((n.get_pixelsize_meters()[0]+n.get_pixelsize_meters()[1])/2.),
                 resample_alg=0)

    metadata = n.get_metadata()
    title = n.get_metadata("title")
    title_no = n.get_metadata("title_no")
    summary = n.get_metadata("summary")
    summary_no = n.get_metadata("summary_no")
    history = n.get_metadata("history")
    tstart = n.get_metadata("time_coverage_start")

    # Remove all metadata before projecting the data (to avoid issue
    # with special characters)
    n.vrt.dataset.SetMetadata({})
    n.reproject(model)
    n.vrt.dataset.SetMetadata({"history": history})

    # Set new filename
    time = datetime.datetime.fromisoformat(tstart)
    year = f"{time.year:04d}"
    month = f"{time.month:02d}"
    day = f"{time.day:02d}"
    pp = Path(os.path.join(args.output_path, year, month, day))
    pp.mkdir(exist_ok=True, parents=True)
    filename = os.path.join(args.output_path, year, month, day,
                            "reprojected_" + os.path.basename(args.sarwind))
    if os.path.isfile(filename):
        logging.debug("%s already exists" % filename)
        return

    # Export
    n.export(filename)
    created = datetime.datetime.now(pytz.timezone("utc")).isoformat()

    # Copy and update metadata
    ds = netCDF4.Dataset(filename, "a")
    # Make new metadata ID
    metadata["id"] = str(uuid.uuid4())
    # Set new date_created
    metadata["date_created"] = created
    # Change title
    metadata["title"] = "Map projected s" + title[1:]
    metadata["title_no"] = "Kartprojisert o" + title_no[1:]
    # Change summary
    metadata["summary"] = "Map projected s" + summary[1:]
    metadata["summary_no"] = "Kartprojisert o" + summary_no[1:]
    # Update history
    metadata["history"] = ds.history + "\n%s: reproject to %s grid mapping" % (
        created, ds["windspeed"].grid_mapping)

    # Remove not needed metadata
    ds.delncattr("NANSAT_GeoTransform")
    ds.delncattr("NANSAT_Projection")
    ds.delncattr("filename")
    ds["swathmask"].delncattr("wkv")
    ds["swathmask"].delncattr("colormap")
    ds["swathmask"].delncattr("PixelFunctionType")

    # Remove wrong metadata
    ds["swathmask"].delncattr("standard_name")

    # Remove old history
    ds.delncattr("history")

    # Add metadata to nc-file
    ds.setncatts(metadata)
    ds.close()

    logging.info("Reprojected wind field stored as %s" % filename)

    statusm, msgm = export_mmd(filename, args.nc_target_path, args.odap_target_url,
                               parent_mmd=args.parent_mmd)


def _main():  # pragma: no cover
    main(create_parser().parse_args())  # entry point in setup.cfg


if __name__ == '__main__':  # pragma: no cover
    main(create_parser().parse_args())
