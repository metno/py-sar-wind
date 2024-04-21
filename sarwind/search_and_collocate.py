import datetime

from pytz import timezone

from collocation.with_dataset import SearchCSW
from collocation.with_dataset import AromeArctic
from collocation.with_dataset import Meps


def get_sar(time=None, dt=24, bbox=None, endpoint="https://nbs.csw.met.no/csw"):

    text = "Sentinel-1"
    # Find all Sentinel-1 data dt/2 hours back in time from now:
    sar = SearchCSW(time=time, dt=dt, text=text, endpoint=endpoint)

    return sar.urls
