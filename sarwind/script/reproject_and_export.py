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
        "--odap_target_url", type=str, default=None,
        help="Root folder of the OPeNDAP target url."
    )
    parser.add_argument(
        "--log_to_file", action="store_true",
        help="Log to file instead of the console."
    )
    parser.add_argument(
        "--log_file", type=str, default="process-sar-wind.log",
        help="Log file name."
    )
    parser.add_argument(
        "--wms_base_url", type=str, default=None,
        help="Base of OGC WMS url."
    )

    return parser


def main(args=None):
    """Reproject and export SAR wind to a new dataset.
    """
    if args.log_to_file:
        logging.basicConfig(filename=args.log_file, level=logging.INFO)
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
    filename = "reprojected_" + os.path.basename(args.sarwind)
    full_path = os.path.join(args.output_path, year, month, day, filename)
    if os.path.isfile(full_path):
        logging.debug("%s already exists" % full_path)
        return

    # Export
    n.export2thredds(full_path, time=time)
    created = datetime.datetime.now(pytz.timezone("utc")).isoformat()

    # Copy and update metadata
    ds = netCDF4.Dataset(full_path, "a")
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
    metadata["history"] = history + "\n%s: reproject to %s grid mapping" % (
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

    logging.info("Reprojected wind field stored as %s" % full_path)

    add_wms = False
    wms_layers = None
    wms_url = None
    if args.wms_base_url is not None:
        add_wms = True
        wms_layers = ["windspeed"]
        wms_url = os.path.join(args.wms_base_url, year, month, day, filename)

    statusm, msgm = export_mmd(full_path, args.odap_target_url,
                               parent=args.parent_mmd, add_wms_data_access=add_wms,
                               wms_link=wms_url, wms_layer_names=wms_layers)


def _main():  # pragma: no cover
    main(create_parser().parse_args())  # entry point in setup.cfg


if __name__ == '__main__':  # pragma: no cover
    main(create_parser().parse_args())
