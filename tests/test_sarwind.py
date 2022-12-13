import os
import pytest


from sarwind.sarwind import get_nansat
from sarwind.sarwind import SARWind

# Se oppsett og eksempler i https://github.com/metno/discovery-metadata-catalog-ingestor/
# ang testing. Evt søk i google...
sar_ds = 'http://nbstds.met.no/thredds/dodsC/NBS/S1A/2021/03/24/EW/S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.nc'
arome_ds = 'https://thredds.met.no/thredds/dodsC/aromearcticarchive/2021/03/24/arome_arctic_vtk_20210324T03Z.nc'
sar_file = 'http://nbstds.met.no/thredds/fileServer/NBS/S1A/2021/03/24/EW/S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.nc'
arome_file = 'https://thredds.met.no/thredds/fileServer/aromearcticarchive/2021/03/24/arome_arctic_vtk_20210324T03Z.nc'
meps_file = '/lustre/storeB/project/metproduction/products/meps/member_00/meps_det_vdiv_2_5km_20221026T06Z.nc'

@pytest.mark.sarwind
def testSARWind__get_nansat__returns__nansat(filesDir, mocker):
    """Tests that get_nansat returns a Nansat object for both the
    sample datasets.
    """
    # Sample datasets
    sar_ds = os.path.join(filesDir, 'S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.nc')
    arome_ds = os.path.join(filesDir, 'arome_arctic_vtk_20210324T03Z.nc')
    class NansatMocked:
        pass
    mocker.patch("sarwind.sarwind.Nansat", return_value=NansatMocked())
    n = get_nansat(sar_ds)
    assert type(n) is NansatMocked
    w = get_nansat(arome_ds)
    assert type(w) is NansatMocked

def testSARWind__get_aux_wind_from_str__returns__wdir(filesDir, mocker):
    """Tests that calls function _get_aux_wind_from_str.
    """

    arome_ds = os.path.join(filesDir, 'arome_arctic_vtk_20210324T03Z_subsample_v2.nc')
    class wdirMocked:
        pass

    mocker.patch("sarwind.sarwind.SARWind._get_aux_wind_from_str", return_value=wdirMocked())
    n = SARWind._get_aux_wind_from_str(arome_ds)
    assert type(n) is wdirMocked

def testSARWind_using_s1EWnc_arome_filenames(filesDir):
    """Test that generte wind from Sentinel-1 data in EW-mode,
    DH-polarization and nerCDF format.
    Wind direction from Arome Arctic model.
    """
    sar_ds = os.path.join(filesDir, 'S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C_nansat005.nc')
    model_ds = os.path.join(filesDir, 'arome_arctic_vtk_20210324T03Z_nansat05.nc')

    if os.path.isfile(sar_ds) == False:
        raise IOError ('No SAR data available in :%s' % (sar_ds))

    if os.path.isfile(model_ds) == False:
        raise IOError ('No arome data available in :%s' % (model_ds))

    w = SARWind(sar_ds,model_ds)
    assert type(w) == SARWind


def testSARWind_using_s1EWsafe_meps_filenames(filesDir):
    """Test that generte wind from Sentinel-1 data in EW-mode,
    DH-polarization and SAFE format.
    Wind direction from MEPS model.
    """
    #sar_ds = os.path.join(filesDir, 'S1A_EW_GRDM_1SDH_20221026T054324_20221026T054411_045609_05740B_6B3F.SAFE')
    sar_ds = os.path.join(filesDir, 'S1A_EW_GRDM_1SDH_20221026T054324_20221026T054411_045609_05740B_6B3F.SAFE_nansat005.nc')
    model_ds = os.path.join(filesDir, 'meps_det_vdiv_2_5km_20221026T06Z_nansat05.nc')

    if ((os.path.isdir(sar_ds)== False) & (os.path.isfile(sar_ds)== False)):
        raise IOError ('No SAR data available in :%s' % (sar_ds))

    if os.path.isfile(model_ds) == False:
        raise IOError ('No arome data available in :%s' % (model_ds))

    w = SARWind(sar_ds,model_ds)
    assert type(w) == SARWind


def testSARWind_using_s1IWDVsafe_meps_filenames(filesDir):
    """Test that generte wind from Sentinel-1 data in IW-mode,
    DV-polarization and SAFE format.
    Wind direction from MEPS model.
    """
    #sar_ds = os.path.join(filesDir, 'S1A_IW_GRDH_1SDV_20221026T054447_20221026T054512_045609_05740C_2B2A.SAFE')
    sar_ds = os.path.join(filesDir, 'S1A_IW_GRDH_1SDV_20221026T054447_20221026T054512_045609_05740C_2B2A.SAFE_nansat005.nc')
    #model_ds = os.path.join(filesDir, 'meps_det_vdiv_2_5km_20221026T06Z.nc')
    model_ds = os.path.join(filesDir, 'meps_det_vdiv_2_5km_20221026T06Z_nansat05.nc')

    if ((os.path.isdir(sar_ds) == False) & (os.path.isfile(sar_ds)== False)):
        raise IOError ('No SAR data available in :%s' % (sar_ds))

    if os.path.isfile(model_ds) == False:
        raise IOError ('No arome data available in :%s' % (model_ds))

    w = SARWind(sar_ds,model_ds)
    assert type(w) == SARWind

