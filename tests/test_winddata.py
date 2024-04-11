import pytest
import datetime

from winddata.winddata import WINDdata
import pytz
from owslib import fes
from unittest import mock


@pytest.mark.unittests
@pytest.mark.winddata
def testWINDdata_input_parameter():
    """ Test setting up CSW cronstrains from input parameters
    """
    """ Freetext search """
    kw_names = 'Arome-Arctic%'
    or_filt = WINDdata._get_freetxt_search([], kw_names)
    assert type(or_filt) == fes.PropertyIsLike

    """ Restricting search from start,stop time """
    stop = datetime.datetime(2023, 4, 17, 0, 00, 00).replace(tzinfo=pytz.utc)
    start = stop - datetime.timedelta(days=1)
    begin, end = WINDdata._fes_date_filter([], start, stop)
    assert isinstance(begin, fes.PropertyIsGreaterThanOrEqualTo)
    assert isinstance(end, fes.PropertyIsLessThanOrEqualTo)

    """ Restricting search from boundering box """
    bbox = [-10, 75, 40, 85]
    crs = 'urn:ogc:def:crs:OGC:1.3:CRS84'
    bbox_crs = fes.BBox(bbox, crs=crs)
    assert isinstance(bbox_crs, fes.BBox)


@pytest.mark.winddata
@mock.patch("winddata.winddata.WINDdata._get_csw_records")
@mock.patch("winddata.winddata.WINDdata._get_csw_connection")
def testWINDdata_from_thredds(mock_csw, mock_get_csw_records):
    """ Test using CSW for reading Sentinel-1 data.
        This test requres access to https://csw.s-enda.k8s.met.no/csw
    """
    class Mycsw_class:
        records = {}

    class Myval_class:
        references = []

    myrec_val = Myval_class
    myrec_val.references = [
        {'scheme': 'OPENDAP:OPENDAP',
         'url': 'https://thredds.met.no/thredds/dodsC/aromearcticarchive/'
         '2023/04/16/arome_arctic_det_2_5km_20230416T06Z.nc'},
        {'scheme': 'OGC:WMS',
         'url': 'https://thredds.met.no/thredds/wms/aromearcticarchive/'
         '2023/04/16/arome_arctic_det_2_5km_20230416T06Z.nc'
         '?service=WMS&version=1.3.0&request=GetCapabilities'},
        {'scheme': 'download',
         'url': 'https://thredds.met.no/thredds/fileServer/aromearcticarchive'
         '/2023/04/16/arome_arctic_det_2_5km_20230416T06Z.nc'},
        {'scheme': None,
         'url': "https://thredds.met.no/thredds/fileServer/aromearcticarchive')/$value"}
    ]

    mycsw = Mycsw_class
    mycsw.records = {'key1': myrec_val}

    mock_csw.return_value = mycsw()
    mock_get_csw_records.return_value = mycsw()

    for (key, val) in list(mycsw.records.items()):
        print('####################################3')
        sw = WINDdata()
        assert sw.url_opendap[0] == 'https://thredds.met.no/thredds/dodsC/aromearcticarchive/'\
            '2023/04/16/arome_arctic_det_2_5km_20230416T06Z.nc'
