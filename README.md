[![flake8](https://github.com/metno/py-sar-wind/actions/workflows/syntax.yml/badge.svg)](https://github.com/metno/py-sar-wind/actions/workflows/syntax.yml)
[![pytest](https://github.com/metno/py-sar-wind/actions/workflows/pytest.yml/badge.svg)](https://github.com/metno/py-sar-wind/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/metno/py-sar-wind/graph/badge.svg?token=fuO0XONBOp)](https://codecov.io/gh/metno/py-sar-wind)

# py-sar-wind

Tools for SAR wind processing.

# Pre-installation requirements

In order to use py-sar-wind, Earth topography data is required to separate
between land and ocean coverage in the SAR data. We use the Mean Statistic, 30
arc-seconds global raster data grids provided by the U.S. Geological Survey
(USGS; https://www.usgs.gov/coastal-changes-and-impacts/gmted2010).

In order to use the topography dataset, launch the GMTED2010 Viewer available
via https://www.usgs.gov/coastal-changes-and-impacts/gmted2010, select all the
regions, and download the "Mean - 30 arc-sec" tif-files. Add the files to a
local folder, and copy the file `gmted2010_30.vrt` in py-sar-wind to the same
folder as the source files (xml and tif).

Finally, add the location of the source files and the VRT file to your
.bashrc-file:
```
export GMTED30=$HOME/GMTED/gmted2010_30.vrt
```

You should now be ready to install py-sar-wind.

# Installation

Create conda environment:
```
conda env create -f sar-wind.yml
```

Activate the new environment:
```
conda activate sarwind
```

Install remaining dependencies:
```
pip install .
```

# Usage

Sentinel-1 Synthetic Aperture Radar (SAR) data can be found and downloaded from, e.g.,
https://colhub.met.no/#/home provided user registration.

Since wind direction cannot be estimated directly from the SAR Normalized Radar
Cross Section (NRCS), auxiliary wind direction data needs to be provided. This
can be, e.g., numerical weather forecast models such as MEPS and AROME-ARCTIC
in Norwegian areas and NCEP GFS globally, or reanalysis products like ERA5.

The simplest way to use py-sar-wind is to download a Sentinel-1 product, and
use the global NCEP GFS dataset to get wind directions:
```
from sarwind.sarwind import SARWind

model_fn = ("https://pae-paha.pacioos.hawaii.edu/thredds/dodsC/"
            "ncep_global/NCEP_Global_Atmospheric_Model_best.ncd")
sar_fn = "S1A_EW_GRDM_1SDV_20241103T024443_20241103T024549_056384_06E87A_B5A4.zip"

w = SARWind(sar_fn, model_fn)
```

Quick look at the data:
```
from swutils.utils import plot_wind_map
plot_wind_map(w)
```

Export to netCDF:
```
w.export("S1A_EW_GRDM_1SDV_20241103T024443_20241103T024549_056384_06E87A_B5A4.nc")
```

![Example wind field](https://github.com/metno/py-sar-wind/blob/main/example.png)
