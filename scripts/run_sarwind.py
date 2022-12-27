import sys
import argparse
import warnings
from datetime import datetime
from dateutil.parser import parse

from sarwind.sarwind import SARWind


###################################
#    If run from command line
###################################
def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='SAR_filename',
                        required=True, help='SAR image filename')
    parser.add_argument('-w', dest='wind_direction',
            required = True,
            help='Wind direction model filename')
    parser.add_argument('-n', dest='netCDF',
            help='Export numerical output to NetCDF file')
    parser.add_argument('-f', dest='figure_filename',
            help='Save wind plot as figure (e.g. PNG or JPEG)')
    parser.add_argument('-p', dest='pixelsize', default=500,
            help='Pixel size for SAR wind calculation (default = 500 m)',
                type=float)
    return parser



if __name__ == '__main__':

    parser = create_parser()
    args = parser.parse_args()

    if args.figure_filename is None and args.netCDF is None:
        raise ValueError('Please add filename of processed figure (-f) or' \
                ' netcdf (-n)')

    # Read SAR image
    sw = SARWind(args.SAR_filename, args.wind_direction, pixelsize=args.pixelsize)

    # Save figure
    if args.figure_filename is not None:
        print('Saving output as figure: ' + args.figure_filename)
        plt = plot(sw, filename=args.figure_filename, show=False)

    # Save as netCDF file
    if args.netCDF is not None:
        print('Saving output to netCDF file: ' + args.netCDF)
        sw.export(args.netCDF, bands=None)  # Exporting windspeed and dir
