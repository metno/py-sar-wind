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
    process_sar_wind [-h] -t TIME -dt HOURS [-m FORECAST_MODEL]

Examples:

    # Process wind in all areas covered by MET Norway's weather
    # forecast models
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24

    # Process wind in meps region
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24 -m meps

    # Process wind in Arome-Arctic region
    process_sar_wind -t 2024-04-22T12:00:00Z -dt 24 -m arome-arctic
"""


