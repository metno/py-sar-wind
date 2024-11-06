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

from nansat.nansat import Nansat


def plot_ncep_wind(time_str="2024-10-27T16:37:52.726330"):
    cb = True
    dp = 15
    wfn = ("https://pae-paha.pacioos.hawaii.edu/thredds/dodsC/"
           "ncep_global/NCEP_Global_Atmospheric_Model_best.ncd")
    n = Nansat(wfn, netcdf_dim={"time": np.datetime64(time_str)})
    lon, lat = n.get_geolocation_grids()
    vv = n["vgrd10m"]
    uu = n["ugrd10m"]
    speed = np.sqrt(np.square(uu) + np.square(vv))

    da = xr.DataArray(speed, dims=["y", "x"],
                      coords={"lat": (("y", "x"), lat), "lon": (("y", "x"), lon)})

    ax1 = plt.subplot(projection=ccrs.PlateCarree())
    da.plot.pcolormesh("lon", "lat", ax=ax1, vmin=0, vmax=18, cmap=cmocean.cm.speed,
                       add_colorbar=cb)
    du = xr.DataArray(uu[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), lat[::dp, ::dp]),
                              "lon": (("y", "x"), lon[::dp, ::dp])})
    dv = xr.DataArray(vv[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), lat[::dp, ::dp]),
                              "lon": (("y", "x"), lon[::dp, ::dp])})
    ds = xr.Dataset({"du": du, "dv": dv})
    ds.plot.quiver(x="lon", y="lat", u="du", v="dv", ax=ax1, angles="xy", headwidth=2,
                   width=0.001)
    ax1.add_feature(cfeature.COASTLINE)
    ax1.gridlines(draw_labels=True)

    plt.show()


def plot_wind_map(w, vmin=0, vmax=20, title=None):
    """ Plot a map of the wind field in w.
    """
    cb = True
    dp = 15
    mlon, mlat = w.get_geolocation_grids()

    # NRCS
    try:
        s0_band_no = w.get_band_number({
            "standard_name": "surface_backwards_scattering_coefficient_of_radar_wave",
            "polarization": "HH"})
    except ValueError:
        s0_band_no = w.get_band_number({
            "standard_name": "surface_backwards_scattering_coefficient_of_radar_wave",
            "polarization": "VV"})
    sda = xr.DataArray(10.*np.log10(w[s0_band_no]), dims=["y", "x"],
                       coords={"lat": (("y", "x"), mlat), "lon": (("y", "x"), mlon)})

    # FIG 1
    ax1 = plt.subplot(1, 3, 1, projection=ccrs.PlateCarree())
    sda.plot.pcolormesh("lon", "lat", ax=ax1, vmin=-20, vmax=0, cmap="gray",
                        add_colorbar=cb)
    ax1.add_feature(cfeature.LAND, zorder=100, edgecolor='k')
    ax1.gridlines(draw_labels=True)
    ax1.title.set_text("NRCS")

    # Wind direction
    dir_from_band_no = w.get_band_number({"standard_name": "wind_from_direction"})
    wind_from = w[dir_from_band_no]

    # Model wind
    model_wspeed_band_no = w.get_band_number({"standard_name": "wind_speed",
                                              "long_name": "Model wind speed"})
    mwspeed = w[model_wspeed_band_no]
    muu = - mwspeed * np.sin(wind_from * np.pi / 180.0)
    mvv = - mwspeed * np.cos(wind_from * np.pi / 180.0)
    mda = xr.DataArray(mwspeed, dims=["y", "x"],
                       coords={"lat": (("y", "x"), mlat), "lon": (("y", "x"), mlon)})

    # FIG 2
    ax2 = plt.subplot(1, 3, 2, projection=ccrs.PlateCarree())
    mda.plot.pcolormesh("lon", "lat", ax=ax2, vmin=vmin, vmax=vmax, cmap=cmocean.cm.speed,
                        add_colorbar=cb)
    mdu = xr.DataArray(muu[::dp, ::dp], dims=["y", "x"],
                       coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                               "lon": (("y", "x"), mlon[::dp, ::dp])})
    mdv = xr.DataArray(mvv[::dp, ::dp], dims=["y", "x"],
                       coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                               "lon": (("y", "x"), mlon[::dp, ::dp])})
    mds = xr.Dataset({"mdu": mdu, "mdv": mdv})
    mds.plot.quiver(x="lon", y="lat", u="mdu", v="mdv", ax=ax2, angles="xy", headwidth=2,
                    width=0.001)
    ax2.add_feature(cfeature.LAND, zorder=100, edgecolor='k')
    ax2.gridlines(draw_labels=True)
    ax2.title.set_text("Model wind field")

    # SAR wind
    speed_band_no = w.get_band_number({"standard_name": "wind_speed",
                                       "long_name": "CMOD5n wind speed"})
    wspeed = w[speed_band_no]

    uu = - wspeed * np.sin(wind_from * np.pi / 180.0)
    vv = - wspeed * np.cos(wind_from * np.pi / 180.0)

    sda = xr.DataArray(wspeed, dims=["y", "x"],
                       coords={"lat": (("y", "x"), mlat), "lon": (("y", "x"), mlon)})

    # FIG 3
    ax3 = plt.subplot(1, 3, 3, projection=ccrs.PlateCarree())
    sda.plot.pcolormesh("lon", "lat", ax=ax3, vmin=vmin, vmax=vmax, cmap=cmocean.cm.speed,
                        add_colorbar=cb)

    du = xr.DataArray(uu[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                              "lon": (("y", "x"), mlon[::dp, ::dp])})
    dv = xr.DataArray(vv[::dp, ::dp], dims=["y", "x"],
                      coords={"lat": (("y", "x"), mlat[::dp, ::dp]),
                              "lon": (("y", "x"), mlon[::dp, ::dp])})
    ds = xr.Dataset({"du": du, "dv": dv})
    ds.plot.quiver(x="lon", y="lat", u="du", v="dv", ax=ax3, angles="xy", headwidth=2, width=0.001)

    ax3.add_feature(cfeature.LAND, zorder=100, edgecolor='k')
    ax3.gridlines(draw_labels=True)
    ax3.title.set_text("SAR wind speed")
    # if title is None:
    #     plt.title('Wind on %s' % w.time_coverage_start.strftime('%Y-%m-%d'))

    plt.show()
