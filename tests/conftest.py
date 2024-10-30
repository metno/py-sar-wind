"""
met-sar-vind : Test Config
==================

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
import shutil
import pytest

from pathlib import Path

# Note: This line forces the test suite to import the sarwind package
# in the current source tree
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

##
#  Directory Fixtures
##


@pytest.fixture(autouse=True)
def no_mkdir(monkeypatch):
    monkeypatch.setattr("os.mkdir", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def no_Path_dot_mkdir(monkeypatch):
    monkeypatch.setattr(Path, "__init__", lambda *a, **k: None)
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: None)


@pytest.fixture(scope="session")
def rootDir():
    """The root folder of the repository."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))


@pytest.fixture(scope="session")
def tmpDir():
    """A temporary folder for the test session. This folder is
    presistent after the tests have run so that the status of generated
    files can be checked. The folder is instead cleared before a new
    test session.
    """
    testDir = os.path.dirname(__file__)
    theDir = os.path.join(testDir, "temp")
    if os.path.isdir(theDir):
        shutil.rmtree(theDir)
    if not os.path.isdir(theDir):
        os.mkdir(theDir)
    return theDir


@pytest.fixture(scope="session")
def filesDir():
    """A path to the reference files folder."""
    testDir = os.path.dirname(__file__)
    theDir = os.path.join(testDir, "files")
    return theDir


@pytest.fixture(scope="session")
def sarEW_NBS(filesDir):
    """Test file based on NBS netcdf-cf formatted data. Contains
    ice."""
    filename = "S1A_EW_GRDM_1SDH_20210324T035507_20210324T035612_037135_045F42_5B4C.NBS.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def sarEW_SAFE(filesDir):
    """Test file based on SAFE formatted data. Contains land and
    water."""
    filename = "S1A_EW_GRDM_1SDH_20221026T054324_20221026T054411_045609_05740B_6B3F.SAFE.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def sarIW_SAFE(filesDir):
    """Test file based on SAFE formatted data. Contains water (and a
    wind front(?))."""
    filename = "S1A_IW_GRDH_1SDV_20221026T054447_20221026T054512_045609_05740C_2B2A.SAFE.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def s1a_20240416(filesDir):
    """ Test file with id and naming_authority.
    """
    filename = "S1A_IW_GRDM_1SDV_20240416T171946_20240416T172013_053462_067C88_E676.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def meps_20240416(filesDir):
    """ Test file with id and naming_authority.
    """
    filename = "meps_mbr000_sfc_20240416T18Z.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def meps(filesDir):
    filename = "meps_det_vdiv_2_5km_20221026T06Z_nansat05.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="session")
def arome(filesDir):
    filename = "arome_arctic_vtk_20210324T03Z_nansat.nc"
    return os.path.join(filesDir, filename)


@pytest.fixture(scope="function")
def fncDir(tmpDir):
    """A temporary folder for a single test function."""
    fncDir = os.path.join(tmpDir, "f_temp")
    if os.path.isdir(fncDir):
        shutil.rmtree(fncDir)
    if not os.path.isdir(fncDir):
        os.mkdir(fncDir)
    return fncDir


##
#  Mock Files
##


##
#  Objects
##
class MockNansat:
    """Mock of Nansat class
    """
    time_coverage_start = "2024-04-04T23:22:31+00:00"

    def __init__(self, *a, **k):
        return None

    def set_metadata(self, *args, **kwargs):
        return None

    def has_band(self, *args, **kwargs):
        return None

    def add_band(self, *args, **kwargs):
        return None

    def get_band_number(self, *args, **kwargs):
        return None

    def resize(self, *args, **kwargs):
        return None

    def reproject(self, *args, **kwargs):
        return None

    def get_metadata(self, *args, **kwargs):
        return None

    def intersects(self, *args, **kwargs):
        return None

    def __getitem__(self, *args, **kwargs):
        return None


class MockNSR:
    pass


class MockDomain:
    pass


class mocked_nansat:
    """Mock of nansat module
    """
    Nansat = MockNansat
    NSR = MockNSR
    Domain = MockDomain


@pytest.fixture(scope="function")
def mock_nansat(monkeypatch):
    """Mocks nansat module and Nansat class
    """
    # The following needs to be done if nansat is installed but the
    # code is still incomplete
    # monkeypatch.setattr("nansat.nansat.Nansat.__init__", lambda *a, **k: MockNansat())
    # monkeypatch.setattr("nansat.Nansat.__init__", lambda *a, **k: MockNansat())
    # monkeypatch.setattr("nansat.Nansat.set_metadata", lambda *a, **k: None)
    # monkeypatch.setattr("nansat.Nansat.has_band", lambda *a, **k: None)
    # monkeypatch.setattr("nansat.Nansat.get_band_number", lambda *a, **k: None)
    # monkeypatch.setattr("nansat.Nansat.resize", lambda *a, **k: None)
    # monkeypatch.setattr("nansat.Nansat.__get_item__", lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "nansat", mocked_nansat())
    monkeypatch.setitem(sys.modules, "nansat.nsr", mocked_nansat())
    monkeypatch.setitem(sys.modules, "nansat.domain", mocked_nansat())
    monkeypatch.setitem(sys.modules, "nansat.nansat", mocked_nansat())
    monkeypatch.setattr("sarwind.sarwind.Nansat", MockNansat)


@pytest.fixture(scope="function")
def mock_nsr(monkeypatch):
    """Mocks Domain class
    """
    monkeypatch.setattr("sarwind.sarwind.NSR", MockNSR)


@pytest.fixture(scope="function")
def mock_domain(monkeypatch):
    """Mocks Domain class
    """
    monkeypatch.setattr("sarwind.sarwind.Domain", MockDomain)
