import sys
import argparse
import warnings
from datetime import datetime
from dateutil.parser import parse

from matplotlib import pyplot as plt
from matplotlib import cm
import numpy as np

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

def plot(sw, filename=None, numVectorsX = 16, show=True,
        clim=[0,20], maskWindAbove=35,
        windspeedBand='windspeed', winddirBand='winddirection',
        northUp_eastRight=True, landmask=True, icemask=True):
    """ Basic plotting function showing CMOD wind speed
    overlaid vectors in SAR image projection

    parameters
    ----------
    filename : string
    numVectorsX : int
        Number of wind vectors along first dimension
    show : Boolean
    clim : list
        Color limits of the image.
    windspeedBand : string or int
    winddirBand : string or int
    landmask : Boolean
    icemask : Boolean
    maskWindAbove : int

    """

    try:
        sar_windspeed, palette = sw._get_masked_windspeed(landmask,
                icemask, windspeedBand=windspeedBand)
    except:
        raise ValueError('SAR wind has not been calculated, ' \
            'execute calculate_wind(wind_direction) before plotting.')
    sar_windspeed[sar_windspeed>maskWindAbove] = np.nan

    winddirReductionFactor = int(np.round(
            sw.vrt.dataset.RasterXSize/numVectorsX))

    winddir_relative_up = 360 - sw[winddirBand] + \
                                sw.azimuth_y()
    indX = range(0, sw.vrt.dataset.RasterXSize, winddirReductionFactor)
    indY = range(0, sw.vrt.dataset.RasterYSize, winddirReductionFactor)
    X, Y = np.meshgrid(indX, indY)
    try: # scaling of wind vector length, if model wind is available
        model_windspeed = sw['model_windspeed']
        model_windspeed = model_windspeed[Y, X]
    except:
        model_windspeed = 8*np.ones(X.shape)

    Ux = np.sin(np.radians(winddir_relative_up[Y, X]))*model_windspeed
    Vx = np.cos(np.radians(winddir_relative_up[Y, X]))*model_windspeed

    # Make sure North is up, and east is right
    if northUp_eastRight:
        lon, lat = sw.get_corners()
        if lat[0] < lat[1]:
            sar_windspeed = np.flipud(sar_windspeed)
            Ux = -np.flipud(Ux)
            Vx = -np.flipud(Vx)
        if lon[0] > lon[2]:
            sar_windspeed = np.fliplr(sar_windspeed)
            Ux = np.fliplr(Ux)
            Vx = np.fliplr(Vx)

    # Plotting
    figSize = sar_windspeed.shape
    legendPixels = 60.0
    legendPadPixels = 5.0
    legendFraction = legendPixels/figSize[0]
    legendPadFraction = legendPadPixels/figSize[0]
    dpi=100.0

    fig = plt.figure()
    fig.set_size_inches((figSize[1]/dpi, (figSize[0]/dpi)*
                            (1+legendFraction+legendPadFraction)))
    ax = fig.add_axes([0,0,1,1+legendFraction])
    ax.set_axis_off()
    plt.imshow(sar_windspeed, cmap=palette, interpolation='nearest')
    plt.clim(clim)
    cbar = plt.colorbar(orientation='horizontal', shrink=.80,
                 aspect=40,
                 fraction=legendFraction, pad=legendPadFraction)
    cbar.ax.set_ylabel('[m/s]', rotation=0) # could replace m/s by units from metadata
    cbar.ax.yaxis.set_label_position('right')
    # TODO: plotting function should be improved to give
    #       nice results for images of all sized
    ax.quiver(X, Y, Ux, Vx, angles='xy', width=0.004,
                scale=200, scale_units='width',
                color=[.0, .0, .0], headaxislength=4)
    if filename is not None:
        fig.savefig(filename, pad_inches=0, dpi=dpi)
    if show:
        plt.show()
    return fig




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
        plt = plot(sw,filename=args.figure_filename, show=False)

    # Save as netCDF file
    if args.netCDF is not None:
        print('Saving output to netCDF file: ' + args.netCDF)
        sw.export(args.netCDF, bands=None)  # Exporting windspeed and dir
