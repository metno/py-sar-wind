import os
import pytest
import netCDF4
import tempfile

import numpy as np

from unittest.mock import Mock

nansat_installed = True
try:
    import nansat  # noqa
except ModuleNotFoundError:
    nansat_installed = False


class SelectMock(Mock):
    pass


@pytest.mark.skipif(nansat_installed, reason="Only works when nansat is not installed")
@pytest.mark.without_nansat
def testSARWind_init(mock_nansat, monkeypatch):
    """ Test init
    """
    from sarwind.sarwind import SARWind

    with pytest.raises(ValueError) as ee:
        SARWind(1, 2)
    assert str(ee.value) == ("Input parameter for SAR and wind "
                             "direction must be of type string")

    with monkeypatch.context() as mp:
        mp.setattr("sarwind.sarwind.Nansat.__init__", lambda *a, **k: None)
        mp.setattr("sarwind.sarwind.Nansat.set_metadata", lambda *args, **kwargs: 1)
        mp.setattr("sarwind.sarwind.Nansat.has_band", lambda *args, **kwargs: True)

        with pytest.raises(Exception) as ee:
            SARWind("sar.nc", "model.nc")
        assert str(ee.value) == "Wind speed already calculated"

        mp.setattr("sarwind.sarwind.Nansat.__init__", lambda *a, **k: None)
        mp.setattr("sarwind.sarwind.Nansat.has_band", lambda *args, **kwargs: False)
        mp.setattr("sarwind.sarwind.Nansat.get_band_number", lambda *args, **kwargs: 1)
        mp.setattr("sarwind.sarwind.Nansat.resize", lambda *args, **kwargs: 1)
        mp.setattr("sarwind.sarwind.Nansat.reproject", lambda *args, **kwargs: None)
        mp.setattr("sarwind.sarwind.Nansat.__getitem__", lambda *args, **kwargs: np.array([1, 1]))
        with pytest.raises(Exception) as ee:
            SARWind("sar.nc", "model.nc")
        assert str(ee.value) == "No SAR NRCS ocean coverage."


@pytest.mark.skipif(nansat_installed, reason="Only works when nansat is not installed")
@pytest.mark.without_nansat
def testSARWind_using_s1EWnc_arome_filenames(mock_nansat, sarEW_NBS, arome, monkeypatch):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and NBS netCDF file with wind direction from the
    Arome Arctic model. We do not need to test SAFE files, as that is
    a Nansat issue.

    S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.NBS.nc
    arome_arctic_vtk_20210324T03Z_nansat05.nc
    """
    from sarwind.sarwind import SARWind
    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [
            np.array([1, 1]),           # self[self.sigma0_bandNo]
            np.array([0, 0]),           # topo[1]
            1,                          # self[self.sigma0_bandNo]
        ]
        mp.setattr("sarwind.sarwind.Nansat.__getitem__", smock)
        mp.setattr("sarwind.sarwind.Nansat.intersects", lambda *a, **k: False)
        smock2 = SelectMock()
        smock2.side_effect = [
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "VV",
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "2024-04-04T23:28:31+00:00",
        ]
        mp.setattr("sarwind.sarwind.Nansat.get_metadata", smock2)
        with pytest.raises(ValueError) as ee:
            SARWind(sarEW_NBS, arome)
        assert str(ee.value) == "The SAR and wind datasets do not intersect."

    # Test that sarwind raises exception if the NRCS is NaN
    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [
            np.array([np.nan, np.nan])  # self[self.sigma0_bandNo]
        ]
        mp.setattr("sarwind.sarwind.Nansat.__getitem__", smock)
        smock2 = SelectMock()
        smock2.side_effect = [
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "VV",
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "2024-04-04T23:28:31+00:00",
        ]
        mp.setattr("sarwind.sarwind.Nansat.get_metadata", smock2)
        with pytest.raises(ValueError) as ee:
            SARWind(sarEW_NBS, arome)
        assert str(ee.value) == "Erroneous SAR product - all NRCS values are NaN."

    # Test that sarwind raises exception if the NRCS is only NaN's and zero's
    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [
            np.array([np.nan, np.nan, 0, 0])  # self[self.sigma0_bandNo]
        ]
        mp.setattr("sarwind.sarwind.Nansat.__getitem__", smock)
        smock2 = SelectMock()
        smock2.side_effect = [
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "VV",
            "2024-04-04T23:28:31+00:00",
            "2024-04-04T23:28:51+00:00",
            "2024-04-04T23:28:31+00:00",
        ]
        mp.setattr("sarwind.sarwind.Nansat.get_metadata", smock2)
        with pytest.raises(ValueError) as ee:
            SARWind(sarEW_NBS, arome)
        assert str(ee.value) == "Erroneous SAR product - NRCS values are NaN and 0 only."


@pytest.mark.without_nansat
def testSARWind_get_model_wind_field(mock_nansat, arome, monkeypatch):
    """
    """
    from sarwind.sarwind import SARWind
    from sarwind.sarwind import Nansat

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [
            np.array([0, 0]),
            np.array([1, 1])
        ]
        mp.setattr("sarwind.sarwind.Nansat.__getitem__", smock)

        aux = Nansat(arome)

        speed, dir, time = SARWind.get_model_wind_field(aux)

        assert not np.isnan(speed).all()
        assert not np.isnan(dir).all()


@pytest.mark.skipif(nansat_installed, reason="Only works when nansat is not installed")
@pytest.mark.without_nansat
def testSARWind_set_related_dataset(mock_nansat, monkeypatch):
    """ Test that the related dataset attribute is correctly added
    when it exists in the input datasets.
    """
    from sarwind.sarwind import SARWind

    with monkeypatch.context() as mp:
        mp.setattr("sarwind.sarwind.Nansat.set_metadata", lambda *a, **k: None)
        mp.setattr(SARWind, "__init__", lambda *a, **kw: None)
        w = SARWind("sar_image", "wind")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853", "naming_authority": "no.met"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c", "naming_authority": "no.met"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("no.met:11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "no.met:d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c", "naming_authority": "no.met"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "no.met:d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853", "naming_authority": "no.met"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("no.met:11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)"

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == "11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary)"

        metadata = {}
        auxm = {}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ""


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_init_with_nansat(monkeypatch):
    """ Test init
    """
    from sarwind.sarwind import SARWind
    from sarwind.sarwind import Nansat
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

        mp.setattr(Nansat, "__init__", lambda *a, **k: None)
        mp.setattr(Nansat, "has_band", lambda *args, **kwargs: False)
        mp.setattr(Nansat, "get_band_number", lambda *args, **kwargs: 1)
        mp.setattr(Nansat, "resize", lambda *args, **kwargs: 1)
        mp.setattr(Nansat, "reproject", lambda *args, **kwargs: None)
        mp.setattr(Nansat, "__getitem__", lambda *args, **kwargs: np.array([1, 1]))
        with pytest.raises(Exception) as ee:
            SARWind("sar.nc", "model.nc")
        assert str(ee.value) == "No SAR NRCS ocean coverage."


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_using_s1EWnc_arome_filenames_with_nansat(sarEW_NBS, arome):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and NBS netCDF file with wind direction from the
    Arome Arctic model. We do not need to test SAFE files, as that is
    a Nansat issue.

    S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.NBS.nc
    arome_arctic_vtk_20210324T03Z_nansat05.nc
    """
    from sarwind.sarwind import SARWind
    with pytest.raises(ValueError) as ee:
        SARWind(sarEW_NBS, arome, max_diff_minutes=30)
    assert "Time difference between model and SAR wind field is greater" in str(ee.value)
    with pytest.raises(ValueError) as ee:
        SARWind(sarEW_NBS, arome, max_diff_minutes=60)
    assert str(ee.value) == "The SAR and wind datasets do not intersect."


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_get_model_wind_field_with_nansat(arome):
    """
    """
    from sarwind.sarwind import SARWind
    from sarwind.sarwind import Nansat
    aux = Nansat(arome)
    speed, dir, time = SARWind.get_model_wind_field(aux)
    assert not np.isnan(speed).all()
    assert not np.isnan(dir).all()


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_set_related_dataset_with_nansat(monkeypatch, meps_20240416, s1a_20240416):
    """ Test that the related dataset attribute is correctly added
    when it exists in the input datasets.
    """
    from sarwind.sarwind import SARWind
    w = SARWind(s1a_20240416, meps_20240416, max_diff_minutes=45)

    with monkeypatch.context() as mp:
        mp.setattr("sarwind.sarwind.Nansat.set_metadata", lambda *a, **k: None)
        mp.setattr(SARWind, "__init__", lambda *a, **kw: None)
        w = SARWind("sar_image", "wind")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853", "naming_authority": "no.met"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c", "naming_authority": "no.met"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("no.met:11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "no.met:d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c", "naming_authority": "no.met"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "no.met:d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853", "naming_authority": "no.met"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("no.met:11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ("11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                              "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)")

        metadata = {}
        auxm = {"id": "d1863d82-47b3-4048-9dcd-b4dafc45eb7c"}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)"

        metadata = {"id": "11d33864-75ea-4a36-9a4e-68c5b3e97853"}
        auxm = {}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == "11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary)"

        metadata = {}
        auxm = {}
        related_ds = w.set_related_dataset(metadata, auxm)
        assert related_ds == ""


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_export(monkeypatch, sarIW_SAFE, meps):
    """ Test the export function
    """
    from sarwind.sarwind import SARWind
    fn = "S1A_IW_GRDH_1SDV_20221026T054447_20221026T054512_045609_05740C_2B2A_wind.nc"
    w = SARWind(sarIW_SAFE, meps)
    tit = ("Sea surface wind (10 m above sea level) estimated from Sentinel-1A NRCS, acquired "
           "on 2022-10-26 05:44:47 UTC")
    metadata = {"title": tit}
    w.export(filename=fn, metadata=metadata)
    assert os.path.isfile(fn)
    ds = netCDF4.Dataset(fn)
    assert ds.title == tit
    os.remove(fn)
    # Provide filename and related_dataset
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        metadata = {"related_dataset": "11d33864-75ea-4a36-9a4e-68c5b3e97853 (auxiliary), "
                                       "d1863d82-47b3-4048-9dcd-b4dafc45eb7c (auxiliary)"}
        w.export(filename=fp.name, metadata=metadata)
        ds = netCDF4.Dataset(fp.name)
        assert ds.title == tit
        assert os.path.isfile(fp.name)
    assert not os.path.isfile(fp.name)
    # Provide bands
    bands = ["windspeed"]
    metadata = {"title": tit}
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        w.export(filename=fp.name, bands=bands, metadata=metadata)
        assert os.path.isfile(fp.name)
    assert not os.path.isfile(fp.name)


@pytest.mark.skipif(not nansat_installed, reason="Only works when nansat is installed")
def testSARWind_using_s1IWDV_meps_filenames(sarIW_SAFE, meps):
    """ Test that wind is generated from Sentinel-1 data in IW-mode,
    VV-polarization and SAFE based netcdf file, with wind direction
    from MEPS model.
    """
    from sarwind.sarwind import SARWind
    w = SARWind(sarIW_SAFE, meps)
    assert w.get_metadata("time_coverage_start") == "2022-10-26T05:44:47.271470"
    assert w.get_metadata("time_coverage_end") == "2022-10-26T05:45:12.269558"
    assert isinstance(w, SARWind)


@pytest.mark.without_nansat
def testSARWind_calculate_wind_from_direction(mock_nansat, mock_nsr, mock_domain):
    """ Test that the wind direction becomes correct.
    """
    from sarwind.sarwind import SARWind
    speed = 4
    dir0 = 30
    u = -2
    v = -2*np.sqrt(3)
    assert np.round(np.sqrt(np.square(u) + np.square(v)), decimals=2) == speed
    dir = SARWind.calculate_wind_from_direction(u, v)
    assert np.round(dir, decimals=2) == dir0
