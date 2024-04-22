#!/usr/bin/env python3
"""
Script to process wind speed from SAR NRCS and forecast model wind
direction using CMOD5n.

License:

This file is part of the met-sar-vind repository
<https://github.com/metno/met-sar-vind>.

met-sar-vind is licensed under the Apache License 2.0
<https://github.com/metno/met-sar-vind/blob/master/LICENSE>

Usage:
    process_sar_wind [-h] -t TIME -dt HOURS -o OUTPUT_PATH

Examples:

    # Process wind in all areas covered by MET Norway's weather
    # forecast models
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24

    # Process wind in meps region
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24 -m meps

    # Process wind in Arome-Arctic region
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24 -m arome-arctic
"""
import os
import logging
import argparse
import datetime

from pytz import timezone

from sarwind.search_and_collocate import get_sar
from sarwind.search_and_collocate import collocate_with

from sarwind.sarwind import SARWind


def create_parser():
    """Create parser object.
    """
    parser = argparse.ArgumentParser(
        description="Process wind from SAR NRCS and forecast model wind directions."
    )
    parser.add_argument(
        "-t", "--time", type=str, default=datetime.datetime.now(timezone("utc")).isoformat(),
        help="Central time of SAR data search (ISO format)."
    )
    parser.add_argument(
        "-d", "--delta", type=str, default=24,
        help="Search interval in hours before and after the central time."
    )
    parser.add_argument(
        "-o", "--output_path", type=str, default=".",
        help="Output path of resulting CF-NetCDF file."
    )
    parser.add_argument(
        "-p", "--processed", type=str, default="processed_urls.txt",
        help="Text file with list of processed datasets."
    )

    return parser


def process(url, model, output_path, fn_ending):
    """Process wind from SAR image and model forecast.
    """
    try:
        w = SARWind(url, model)
    except Exception as ee:
        filename = None
        logging.debug("Processing of %s and %s failed with message: "
                      "%s" % (url, model, str(ee)))
    else:
        basename = os.path.basename(w.filename).split(".")[0]
        filename = os.path.join(output_path, basename + fn_ending)
        w.export(filename=filename)
    return filename


def process_with_meps(url, meps, path):
    """Process and export SAR wind using MEPS wind directions.
    """
    return process(url, meps, path, "_MEPS.nc")


def process_with_arome(url, arome, path):
    """Process and export SAR wind using AROME-ARCTIC wind directions.
    """
    return process(url, arome, path, "_AROMEARCTIC.nc")


def main(args=None):
    """Run tools to process wind from SAR.
    """
    sar_urls = get_sar(time=datetime.datetime.fromisoformat(args.time), dt=args.delta)
    with open(args.processed, "r") as fp:
        processed_urls = ", ".join(fp.readlines())
    for url in sar_urls:
        if url in processed_urls:
            logging.debug("Already processed: %s" % url)
            continue
        meps, arome = collocate_with(url)
        if meps is not None:
            fnm = process_with_meps(url, meps, args.output_path)
        if arome is not None:
            fna = process_with_arome(url, arome, args.output_path)
        if fnm is not None:
            logging.info("Processed %s.\n" % fnm)
            with open(args.processed, "a") as fp:
                fp.write("%s: %s\n" % (url, meps))
        if fna is not None:
            logging.info("Processed %s.\n" % fna)
            with open(args.processed, "a") as fp:
                fp.write("%s: %s\n" % (url, arome))


def _main():  # pragma: no cover
    main(create_parser().parse_args())  # entry point in setup.cfg


if __name__ == '__main__':  # pragma: no cover
    main(create_parser().parse_args())
