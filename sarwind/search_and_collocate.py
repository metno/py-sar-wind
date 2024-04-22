import datetime

from pytz import timezone

from collocation.with_dataset import SearchCSW
from collocation.with_dataset import AromeArctic
from collocation.with_dataset import Meps


def get_sar(time=None, dt=24, bbox=None, endpoint="https://nbs.csw.met.no/csw"):
    """Get Sentinel-1 A and B datasets at the given time +/- dt
    hours.

    Input
    =====
    time : datetime.datetime
        Central time of the search. Default now.
    dt : int
        Search interval in hours before and after the central time.
    bbox : list
        Bounding box given by [lon_min, lat_min, lon_max, lat_max]
    endpoint : str
        OGC CSW endpoint used in the search. Default
        https://nbs.csw.met.no/csw
    """
    text = "Sentinel-1"
    # Text search does not work in NBS...
    text = None
    # Find all Sentinel-1 data dt/2 hours back in time from now:
    sar = SearchCSW(time=time, dt=dt, text=text, endpoint=endpoint)

    urls = []
    for url in sar.urls:
        if "S1A" in url or "S1B" in url:
            urls.append(url)

    return urls


def collocate_with(url, endpoint="https://data.csw.met.no"):
    """Given an OPeNDAP url to a dataset, find collocated Arome-Arctic
    and MEPS weather forecasts.

    Input
    =====
    url : str
        OPeNDAP url to the SAR dataset
    endpoint : str
        OGC CSW endpoint used in the search. Default
        https://data.csw.met.no
    """
    meps = Meps(url)
    meps_url = meps.get_odap_url_of_nearest()

    arome = AromeArctic(url)
    arome_url = arome.get_odap_url_of_nearest()

    return meps_url, arome_url
