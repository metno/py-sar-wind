import pytest
import datetime

import numpy as np

from sarwind.sarwind import SARWind

from sardata.sardataNBS import SARData
import pytz
from owslib import fes
from unittest import mock


@pytest.mark.unittests
@pytest.mark.sarwind
def testSARWind__set_aux_wind(monkeypatch):
    """ Test that SARWind.set_aux_wind calls functions
    _get_aux_wind_from_str and Nansat.add_band.
    """
    mock1_called = 0

    def mock1(*a):
        nonlocal mock1_called
        mock1_called += 1
        speed = np.array([12, 10])
        dir = np.array([20, 21])
        time = datetime.datetime(2021, 3, 24, 3, 0)
        return speed, dir, time

    mock2_called = 0

    def mock2(*a, **kw):
        nonlocal mock2_called
        mock2_called += 1

    with monkeypatch.context() as mp:
        mp.setattr(SARWind, "_get_aux_wind_from_str", mock1)
        mp.setattr(SARWind, "add_band", mock2)
        mp.setattr(SARWind, "__init__", lambda *a: None)

        n = SARWind()
        # Check that it works with expected input
        assert n.set_aux_wind('path/to/wind_field_file.nc') is None
        # Check that the mock for _get_aux_wind_from_str is called once
        assert mock1_called == 1
        # Check that the mock for add_band is called twice
        assert mock2_called == 2

        # Check that TypeError is raised if input is of wrong type
        with pytest.raises(TypeError) as e:
            n.set_aux_wind(1)

        assert str(e.value) == "wind must be of type string"


@pytest.mark.nbs
@pytest.mark.sarwind
def testSARWind_using_s1EWnc_arome_filenames(sarEW_NBS, arome):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and NBS netCDF file with wind direction from the
    Arome Arctic model.
    """
    w = SARWind(sarEW_NBS, arome)
    assert type(w) == SARWind


@pytest.mark.safe
@pytest.mark.sarwind
def testSARWind_using_s1EWsafe_meps_filenames(sarEW_SAFE, meps):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and SAFE based netcdf file, with direction from
    the MEPS model.
    """
    w = SARWind(sarEW_SAFE, meps)
    assert type(w) == SARWind


@pytest.mark.safe
@pytest.mark.sarwind
def testSARWind_using_s1IWDVsafe_meps_filenames(sarIW_SAFE, meps):
    """ Test that wind is generated from Sentinel-1 data in IW-mode,
    VV-polarization and SAFE based netcdf file, with wind direction
    from MEPS model.
    """
    w = SARWind(sarIW_SAFE, meps)
    assert type(w) == SARWind


@pytest.mark.sardata
def testSARData_input_parameter():
    """ Test setting up CSW cronstrains from input parameters
    """
    """ Freetext search """
    kw_names='S1A*'
    or_filt = SARData._get_freetxt_search([], kw_names)
    assert type(or_filt) == fes.Or

    """ Restricting search from start,stop time """
    stop = datetime.datetime(2022, 1, 8, 5, 30, 59).replace(tzinfo=pytz.utc)
    start = stop - datetime.timedelta(days=1)
    begin, end = SARData._fes_date_filter([], start, stop)
    assert type(begin) ==  fes.PropertyIsGreaterThanOrEqualTo
    assert type(end) == fes.PropertyIsLessThanOrEqualTo    
    
    """ Restricting search from boundering box """
    bbox = [-10, 75, 40, 85]
    crs='urn:ogc:def:crs:OGC:1.3:CRS84'
    bbox_crs = fes.BBox(bbox, crs=crs)
    assert type(bbox_crs) == fes.BBox
    
    
@pytest.mark.sardata
@mock.patch("sardata.sardataNBS.SARData._get_csw_records")
@mock.patch("sardata.sardataNBS.SARData._get_csw_connection")
def testSARData_from_NBS(mock_csw,mock_get_csw_records):
    """ Test using CSW for reading Sentinel-1 data.
        This test requres access to https://nbs.csw.met.no/csw
    """
    class Mycsw_class:
        records = {}
    
    class Myval_class:
        references = []
        
    myrec_val = Myval_class
    myrec_val.references = [{'scheme': 'OPENDAP:OPENDAP',
                  'url': 'https://nbstds.met.no/thredds/dodsC/NBS/S2B/2022/02/08/S2B_MSIL1C_20220208T103109_N0400_R108_T34WEB_20220208T125524.nc'},
                 {'scheme': 'OGC:WMS',
                  'url': 'https://nbswms.met.no/thredds/wms_ql/NBS/S2B/2022/02/08/S2B_MSIL1C_20220208T103109_N0400_R108_T34WEB_20220208T125524.nc?SERVICE=WMS&REQUEST=GetCapabilities'},
                 {'scheme': 'download',
                  'url': 'https://nbstds.met.no/thredds/fileServer/NBS/S2B/2022/02/08/S2B_MSIL1C_20220208T103109_N0400_R108_T34WEB_20220208T125524.nc'},
                 {'scheme': None,
                  'url': "https://colhub.met.no/odata/v1/Products('2a34c82f-675a-4304-af4b-b1c3d8030824')/$value"}]   
    mycsw = Mycsw_class
    mycsw.records = {'key1':myrec_val}
    
    mock_csw.return_value = mycsw()
    mock_get_csw_records.return_value = mycsw()
    for (key, val) in list(mycsw.records.items()):
        sw = SARData()
        assert sw.url_opendap[0] == 'https://nbstds.met.no/thredds/dodsC/NBS/S2B/2022/02/08/S2B_MSIL1C_20220208T103109_N0400_R108_T34WEB_20220208T125524.nc'
    