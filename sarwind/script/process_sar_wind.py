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

from pathlib import Path
from pytz import timezone

from py_mmd_tools.nc_to_mmd import Nc_to_mmd

from sarwind.sarwind import SARWind
from sarwind.search_and_collocate import get_sar
from sarwind.search_and_collocate import collocate


def create_parser():
    """Create parser object.
    """
    parser = argparse.ArgumentParser(
        description="Process wind from SAR NRCS and forecast model "
                    "wind directions."
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
        "-o", "--output_path", type=str, default=".",
        help="Output path of resulting CF-NetCDF file (default is the"
             " current directory)."
    )
    parser.add_argument(
        "--export_mmd", action="store_true",
        help="Toggle whether to export metadata to MMD files."
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
    # parser.add_argument(
    #     "--log_level", type=str, default=logging.DEBUG
    #     help="Log level (default DEBUG)."
    # )
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


def process(url, model, output_path, fn_ending):
    """Process wind from SAR image and model forecast.
    """
    try:
        w = SARWind(url, model)
    except Exception as ee:
        filename = None
        logging.error("Processing of %s and %s failed with message: "
                      "%s" % (url, model, str(ee)))
    else:
        basename = os.path.basename(w.filename).split(".")[0]
        time = datetime.datetime.fromisoformat(
            w.get_metadata("time_coverage_start").replace("Z", "+00:00"))
        year = f"{time.year:04d}"
        month = f"{time.month:02d}"
        day = f"{time.day:02d}"
        pp = Path(os.path.join(output_path, year, month, day))
        pp.mkdir(exist_ok=True, parents=True)
        filename = os.path.join(output_path, year, month, day, basename + fn_ending)
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


def export_mmd(nc_file, target_path, base_url, parent_mmd=None):
    """Export metadata to MMD.

    Input
    =====
    nc_file : string
        CF-NetCDF filename
    target_path : string
        Target path for the CF-NetCDF files if they need to be moved
        to another storage place than the given output path (default
        is the current directory).
    """
    # TODO: call API instead of using a local installation of
    #       py-mmd-tools. This requires resolution of issue 319 in
    #       py-mmd-tools
    #       (see https://github.com/metno/py-mmd-tools/issues/319)
    pp = nc_file.split("/")
    url = os.path.join(base_url, pp[-4], pp[-3], pp[-2], pp[-1])
    target_fn = os.path.join(target_path, pp[-4], pp[-3], pp[-2], pp[-1])
    if len(pp) > 4:
        folder = "/".join(pp[:-4])
    else:
        folder = "."
    xml_out = os.path.join(folder, "mmd", pp[-4], pp[-3], pp[-2], pp[-1][:-2]+"xml")
    pp = Path(os.path.dirname(xml_out))
    pp.mkdir(exist_ok=True, parents=True)
    md = Nc_to_mmd(nc_file, opendap_url=url, output_file=xml_out,
                   target_nc_filename=target_fn)
    status, msg = md.to_mmd(parent=parent_mmd)

    return status, xml_out


def main(args=None):
    """Run tools to process wind from SAR. Currently MEPS and
    AROME-ARCTIC weather forecast models are used for wind directions.
    If a SAR image overlaps with both model domains, two SAR wind
    fields will be processed.
    """
    if args.log_to_file:
        logging.basicConfig(filename=args.log_file, level=logging.INFO)

    sar_urls0 = get_sar(time=datetime.datetime.fromisoformat(args.time), dt=args.delta)
    processed_urls = ""
    if os.path.isfile(args.processed_files):
        with open(args.processed_files, "r") as fp:
            lines = fp.readlines()
        for line in lines:
            if "Processed" in line:
                processed_urls = "; ".join([processed_urls, line])

    count = 0
    # Avoid duplicate processing
    sar_urls = []
    for url in sar_urls0:
        if url not in sar_urls:
            sar_urls.append(url)

    fna = None
    fnm = None
    for url in sar_urls:
        if url in processed_urls:
            logging.info("Already processed: %s" % url)
            continue
        meps, arome = collocate(url)
        if meps is not None:
            fnm = process_with_meps(url, meps, args.output_path)
        if arome is not None:
            fna = process_with_arome(url, arome, args.output_path)
        if fnm is not None:
            logging.info("Processed %s:%s" % (url, fnm))
            if args.export_mmd:
                statusm, msgm = export_mmd(fnm, args.nc_target_path, args.odap_target_url,
                                           parent_mmd=args.parent_mmd)
            with open(args.processed_files, "a") as fp:
                fp.write("Processed %s and %s: %s\n\n" % (url, meps, fnm))
        if fna is not None:
            logging.info("Processed %s:%s" % (url, fna))
            if args.export_mmd:
                statusa, msga = export_mmd(fna, args.nc_target_path, args.odap_target_url,
                                           parent_mmd=args.parent_mmd)
            with open(args.processed_files, "a") as fp:
                fp.write("Processed %s and %s: %s\n\n" % (url, arome, fna))
        count += 1
        logging.info("%d/%d done" % (count, len(sar_urls)))


def _main():  # pragma: no cover
    main(create_parser().parse_args())  # entry point in setup.cfg


if __name__ == '__main__':  # pragma: no cover
    main(create_parser().parse_args())
