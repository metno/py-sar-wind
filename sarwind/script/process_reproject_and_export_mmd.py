#!/usr/bin/env python3
import os
import uuid
import logging
import netCDF4
import argparse
import datetime

import numpy as np

from pathlib import Path
from pytz import timezone

from py_mmd_tools.nc_to_mmd import Nc_to_mmd

from nansat.nansat import Nansat

from sarwind.sarwind import SARWind
from sarwind.search_and_collocate import get_sar
from sarwind.search_and_collocate import collocate

def create_parser():
    parser = argparse.ArgumentParser(
        description="Process wind from SAR NRCS and forecast model "
                    "wind directions, reproject SAR wind to forecast "
                    "model grid, and export metadata to an MMD xml "
                    "file."
    )

    parser.add_argument(
        "-t", "--time",
        type=str,
        default=datetime.datetime.utcnow().replace(tzinfo=timezone("utc")).isoformat(),
        help="Central time of SAR data search (ISO format)."
    )

    parser.add_argument(
        "-d", "--delta", type=int, default=24,
        help="Search interval in hours before and after the central "
             "time."
    )

    parser.add_argument(
        "-o", "--swath_path", type=str, default=".",
        help="Output path of resulting CF-NetCDF file (default is the"
             " current directory)."
    )

    parser.add_argument(
        "-o", "--reprojected_path", type=str, default=".",
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
        "--wms_base_url", type=str, default=None,
        help="Base of OGC WMS url."
    )

    parser.add_argument(
        "--processed_files", type=str, default="processed.txt",
        help="List of processed datasets."
    )
    parser.add_argument(
        "--log_to_file", action="store_true",
        help="Log to file instead of the console."
    )
    parser.add_argument(
        "--log_file", type=str, default="process-sar-wind.log",
        help="Log file name."
    )

    return parser


