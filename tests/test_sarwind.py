import os
import pytest
import tempfile

import numpy as np

from nansat.nansat import Nansat
from sarwind.sarwind import SARWind


@pytest.mark.sarwind
def testSARWind_init(monkeypatch):
    """ Test init
    """
    with pytest.raises(ValueError) as ee:
        SARWind(1, 2)
    assert str(ee.value) == ("Input parameter for SAR and wind "
                             "direction must be of type string")

    with monkeypatch.context() as mp:
        mp.setattr(Nansat, "__init__", lambda *a, **k: None)
        mp.setattr(Nansat, "set_metadata", lambda *args, **kwargs: 1)
        mp.setattr(Nansat, "has_band", lambda *args, **kwargs: True)
        with pytest.raises(Exception) as ee:
            SARWind("sar.nc", "model.nc")
        assert str(ee.value) == "Wind speed already calculated"


@pytest.mark.sarwind
def testSARWind_using_s1EWnc_arome_filenames(sarEW_NBS, arome):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and NBS netCDF file with wind direction from the
    Arome Arctic model. We do not need to test SAFE files, as that is
    a Nansat issue.

    S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.NBS.nc
    arome_arctic_vtk_20210324T03Z_nansat05.nc
    """
    with pytest.raises(ValueError) as ee:
        SARWind(sarEW_NBS, arome)
    assert str(ee.value) == ("Failing reprojection - make sure the "
                             "datasets overlap in the geospatial domain.")


@pytest.mark.sarwind
def testSARWind_get_model_wind_field(arome):
    """
    """
    aux = Nansat(arome)
    speed, dir = SARWind.get_model_wind_field(aux)
    assert not np.isnan(speed).all()
    assert not np.isnan(dir).all()


@pytest.mark.sarwind
def testSARWind_set_related_dataset(meps_20240416, s1a_20240416):
    """ Test that the related dataset attribute is correctly added
    when it exists in the input datasets.
    """
    w = SARWind(s1a_20240416, meps_20240416)
    reld = ("no.met:11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
            "no.met:d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")
    assert w.get_metadata("related_dataset") == reld
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        w.export(filename=fp.name)
        assert os.path.isfile(fp.name)
    assert not os.path.isfile(fp.name)

@pytest.mark.sarwind
def testSARWind_export(monkeypatch, sarIW_SAFE, meps):
    """ Test the export function
    """
    w = SARWind(sarIW_SAFE, meps)
    # No args
    w.export()
    fn = "S1A_IW_GRDH_1SDV_20221026T054447_20221026T054512_045609_05740C_2B2A_wind.nc"
    assert os.path.isfile(fn)
    os.remove(fn)
    # Provide filename
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        w.export(filename=fp.name)
        assert os.path.isfile(fp.name)
    assert not os.path.isfile(fp.name)
    # Provide bands
    bands = ["x_wind_10m"]
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        w.export(filename=fp.name, bands=bands)
        assert os.path.isfile(fp.name)
    assert not os.path.isfile(fp.name)


@pytest.mark.sarwind
def testSARWind_using_s1IWDV_meps_filenames(sarIW_SAFE, meps):
    """ Test that wind is generated from Sentinel-1 data in IW-mode,
    VV-polarization and SAFE based netcdf file, with wind direction
    from MEPS model.
    """
    w = SARWind(sarIW_SAFE, meps)
    assert isinstance(w, SARWind)


@pytest.mark.sarwind
def testSARWind_calculate_wind_from_direction():
    """ Test that the wind direction becomes correct.
    """
    speed = 4
    dir0 = 30
    u = -2
    v = -2*np.sqrt(3)
    assert np.round(np.sqrt(np.square(u) + np.square(v)), decimals=2) == speed
    dir = SARWind.calculate_wind_from_direction(u, v)
    assert np.round(dir, decimals=2) == dir0
