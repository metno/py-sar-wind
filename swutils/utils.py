""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import cmocean

import numpy as np
import xarray as xr

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def plot_wind_map(w, vmin=0, vmax=20, title=None):
    """ Plot a map of the wind field in w.
    """
    land_f = cfeature.NaturalEarthFeature('physical', 'land', '50m', edgecolor='face',
                                          facecolor='lightgray')

    # FIG 1
    ax1 = plt.subplot(projection=ccrs.PlateCarree())
    ax1.add_feature(land_f)
    cb = True
    mlon, mlat = w.get_geolocation_grids()

    dir_from_band_no = w.get_band_number({"standard_name": "wind_from_direction"})
    wind_from = w[dir_from_band_no]

    speed_band_no = w.get_band_number({"standard_name": "wind_speed"})
    wspeed = w[speed_band_no]

    uu = - wspeed * np.sin(wind_from * np.pi / 180.0)
    vv = - wspeed * np.cos(wind_from * np.pi / 180.0)

    da = xr.DataArray(wspeed, dims=["y", "x"],
                      coords={"lat": (("y", "x"), mlat), "lon": (("y", "x"), mlon)})
    da.plot.pcolormesh("lon", "lat", ax=ax1, vmin=vmin, vmax=vmax, cmap=cmocean.cm.speed,
                       add_colorbar=cb)

    dp = 15
    du = xr.DataArray(uu[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                              "lon": (("y", "x"), mlon[::dp, ::dp])})
    dv = xr.DataArray(vv[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                              "lon": (("y", "x"), mlon[::dp, ::dp])})
    ds = xr.Dataset({"du": du, "dv": dv})
    ds.plot.quiver(x="lon", y="lat", u="du", v="dv", ax=ax1, angles="xy", headwidth=2, width=0.001)

    cb = False
    ax1.add_feature(cfeature.LAND, zorder=100, edgecolor='k')
    ax1.gridlines(draw_labels=True)
    if title is None:
        plt.title('Wind on %s' % w.time_coverage_start.strftime('%Y-%m-%d'))

    plt.show()
