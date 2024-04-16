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

# Note: This line forces the test suite to import the sarwind package
# in the current source tree
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

##
#  Directory Fixtures
##


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
