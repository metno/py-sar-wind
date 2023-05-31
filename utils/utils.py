""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
import cmocean

import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def plot_wind_map(w, vmin=0, vmax=12):
    land_f = cfeature.NaturalEarthFeature('physical', 'land', '50m', edgecolor='face',
        facecolor='lightgray')

    # FIG 1
    ax1 = plt.subplot(projection=ccrs.PlateCarree())
    mlon, mlat = w.get_geolocation_grids()
    ax1.add_feature(land_f)
    da = xr.DataArray(w['windspeed'], dims=["y", "x"], coords={"lat": (("y", "x"), mlat),
                      "lon": (("y", "x"), mlon)})
    da.plot.pcolormesh("lon", "lat", ax=ax1, vmin=vmin, vmax=vmax, cmap=cmocean.cm.balance,
                       add_colorbar=True)
    ax1.coastlines()
    ax1.gridlines(draw_labels=True)
    plt.title('Wind at %s' % m.time_coverage_start.strftime('%Y-%m-%d'))

    # if add_gc:
    #     date = datetime.datetime(
    #         ds.time_coverage_start.year,
    #         ds.time_coverage_start.month,
    #         ds.time_coverage_start.day
    #     )
    #     gc = Dataset.objects.get(entry_title__contains='globcurrent',
    #         time_coverage_start=date)
    #     n = Nansat(gc.dataseturi_set.all()[0].uri)
    #     n.reproject(m, addmask=False)
    #     u = n['eastward_geostrophic_current_velocity']
    #     v = n['northward_geostrophic_current_velocity']
    #     # Add quiver plot...

    plt.show()
    #plt.savefig(png_fn)
