""" License: This file is part of https://github.com/metno/met-sar-vind
             met-sar-vind is licensed under the Apache-2.0 license
             (https://github.com/metno/met-sar-vind/blob/main/LICENSE).
"""
from owslib import fes
from owslib.csw import CatalogueServiceWeb
from netCDF4 import Dataset


class SARData():
    """A class for getting Sentinel-1 CF-NetCDF data from the
    Norwegian Ground Segment (NBS).

    Parameters
    -----------
    endpoint : str
       URL to NBS. Default: https://nbs.csw.met.no/csw
    bbox : float list
       A boundary box for search area specified in latitude and
       longitude bbox = [lon_min, lat_min, lon_max, lat_max]
    start : datetime.datetime
       Start time of the search
    stop :  datetime.datetime
       Stop time of the search
    str_filter : str
       String filter to limit the search, e.g., "S1A_EW_GRDM_1SDH%"

    """

    def __init__(self, bbox, start, stop, str_filter=None, endpoint='https://nbs.csw.met.no/csw',
                 crs='urn:ogc:def:crs:OGC:1.3:CRS84', *args, **kwargs):
        constraints = []

        # connect to the endpoint
        self.csw = CatalogueServiceWeb(endpoint, timeout=60)
            
        begin, end = self._fes_date_filter(start, stop)
        constraints.append(begin)
        constraints.append(end)

        bbox_crs = fes.BBox(bbox, crs=crs)
        constraints.append(bbox_crs)

        if str_filter:
            freetxt_filt = self._get_freetxt_search(str_filter)
            constraints.append(freetxt_filt)

        filter_list = [fes.And(constraints)]

        self._get_csw_records(csw, filter_list, pagesize=10, maxrecords=100)

        self.urls = []

        for key, value in list(csw.records.items()):
            for ref in value.references:
                if ref['scheme'] == 'OPeNDAP:OPeNDAP':
                    self.urls.append(ref['url'])
                    continue

    def _get_freetxt_search(self, str_filter):
        """Returns a CSW search object based on input string.
        """
        freetxt_filt = fes.PropertyIsLike('csw:AnyText',  literal=('%s' % str_filter),
                                          escapeChar='\\', singleChar='?',
                                          wildCard='%', matchCase=True)
        return freetxt_filt

    def _get_csw_records(self, csw, filter_list, pagesize=10, maxrecords=100):
        """
        Iterate `maxrecords`/`pagesize` times until the requested value in
        `maxrecords` is reached.
        """
        csw_records = {}
        startposition = 0
        nextrecord = getattr(self.csw, "results", 1)
        while nextrecord != 0:
            self.csw.getrecords2(
                constraints=filter_list,
                startposition=startposition,
                maxrecords=pagesize,
                outputschema="http://www.opengis.net/cat/csw/2.0.2",
                esn='full',
            )
            csw_records.update(self.csw.records)
            if self.csw.results["nextrecord"] == 0:
                break
            startposition += pagesize + 1  # Last one is included.
            if startposition >= maxrecords:
                break
        self.csw.records.update(csw_records)


        # Connect to the CSW service
        self._set_csw_connection(endpoint=endpoint)

        next_record = 1
        while next_record != 0:
            # Iterate pages until the requested max_records is reached
            self.conn_csw.getrecords2(
                constraints=filter_list,
                startposition=start_position,
                maxrecords=pagesize,
                outputschema="http://www.opengis.net/cat/csw/2.0.2",
                esn='full')
            csw_records.update(self.conn_csw.records)
            next_record = self.conn_csw.results["nextrecord"]
            start_position += pagesize + 1  # Last one is included.
            if start_position >= max_records:
                next_record = 0

    def _fes_date_filter(self, start, stop, constraint="overlaps"):
        """
        Take datetime-like objects and returns a fes filter for date range
        (begin and end inclusive).
        NOTE: Truncates the minutes!!!
        """
        start = start.strftime("%Y-%m-%d %H:00")
        stop = stop.strftime("%Y-%m-%d %H:00")
        if constraint == "overlaps":
            propertyname = "apiso:TempExtent_begin"
            begin = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
            propertyname = "apiso:TempExtent_end"
            end = fes.PropertyIsGreaterThanOrEqualTo(
                propertyname=propertyname, literal=start
            )
        elif constraint == "within":
            propertyname = "apiso:TempExtent_begin"
            begin = fes.PropertyIsGreaterThanOrEqualTo(
                propertyname=propertyname, literal=start
            )
            propertyname = "apiso:TempExtent_end"
            end = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
        else:
            raise NameError("Unrecognized constraint {}".format(constraint))
        return begin, end
