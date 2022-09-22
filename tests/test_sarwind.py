import os
import pytest

from sarwind.sarwind import get_nansat

# Se oppsett og eksempler i https://github.com/metno/discovery-metadata-catalog-ingestor/
# ang testing. Evt søk i google...
sar_ds = 'http://nbstds.met.no/thredds/dodsC/NBS/S1A/2021/03/24/EW/S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.nc'
arome_ds = 'https://thredds.met.no/thredds/dodsC/aromearcticarchive/2021/03/24/arome_arctic_vtk_20210324T03Z.nc'
sar_file = 'http://nbstds.met.no/thredds/fileServer/NBS/S1A/2021/03/24/EW/S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.nc'
arome_file = 'https://thredds.met.no/thredds/fileServer/aromearcticarchive/2021/03/24/arome_arctic_vtk_20210324T03Z.nc'

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
