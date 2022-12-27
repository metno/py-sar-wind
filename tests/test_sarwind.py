import pytest

from sarwind.sarwind import SARWind


# @pytest.mark.sarwind
# def testSARWind__get_aux_wind_from_str__returns__wdir(arome, mocker):
#     """ Test that calls function _get_aux_wind_from_str.
#     """
#
#     class wdirMocked:
#         pass
#
#     mocker.patch("sarwind.sarwind.SARWind._get_aux_wind_from_str", return_value=wdirMocked())
#     print(arome)
#     n = SARWind._get_aux_wind_from_str(arome)
#     assert type(n) is wdirMocked


@pytest.mark.nbs
@pytest.mark.sarwind
def testSARWind_using_s1EWnc_arome_filenames(sarEW_NBS, arome):
    """ Test that wind is generated from Sentinel-1 data in EW-mode,
    HH-polarization and NBS netCDF file with wind direction from the
    Arome Arctic model.
    """
    w = SARWind(sarEW_NBS, arome)
    assert type(w) == SARWind


# @pytest.mark.safe
# @pytest.mark.sarwind
# def testSARWind_using_s1EWsafe_meps_filenames(sarEW_SAFE, meps):
#     """ Test that wind is generated from Sentinel-1 data in EW-mode,
#     HH-polarization and SAFE based netcdf file, with direction from
#     the MEPS model.
#     """
#     w = SARWind(sarEW_SAFE, meps)
#     assert type(w) == SARWind
#
#
# @pytest.mark.safe
# @pytest.mark.sarwind
# def testSARWind_using_s1IWDVsafe_meps_filenames(sarIW_SAFE, meps):
#     """ Test that wind is generated from Sentinel-1 data in IW-mode,
#     VV-polarization and SAFE based netcdf file, with wind direction
#     from MEPS model.
#     """
#     w = SARWind(sarIW_SAFE, meps)
#     assert type(w) == SARWind
