import os
import logging
import subprocess
from datetime
from pytz import timezone
from xml.dom.minidom import parse


class SARData():
    """A class for downloading Sentinel-1 SAR SAFE files from NBS
    (https://colhub.met.no).

    Parameters
    -----------
    date : datetime.datetime
        Specifies the date (UTC) of the data search. If not specified,
        the current day will be used.
    ULX : float/int
        Upper left corner longitude in decimal degree
    ULY : float/int
        Upper left corner latitude in decimal degree
    URX : float/int
        Upper right corner longitude in decimal degree
    URY : float/int
        Upper right corner latitude in decimal degree
    LLX : float/int
        Lower left corner longitude in decimal degree
    LLY : float/int
        Lower left corner latitude in decimal degree
    LRX : float/int
        Lower Right corner longitude in decimal degree
    LRY : float/int
        Lower Right corner latitude in decimal degree

    Example of use:

        Data will be downloaded to RAWDIR and uncompressed.
        New data will be listet in variable sar_safe_list
        ---
        s = SARData()           # Init
        s.get_NBS_ColhubData()  # Download and uncompress
        s.sar_safe_list         # List of data available in RAWDIR
    """

    def __init__(self, date=None, LLX=-180., LLY=-90., LRX=180., LRY=-90., URX=180., URY=90.,
                 ULX=-180., ULY=90.):
        self.date = date
        if self.date is None:
            self.date = datetime.datetime.now(timezone("utc"))

        # Check input
        if not isinstance(time, datetime.datetime):
            raise ValueError("Input time must be of type datetime.datetime")
        if not isinstance(LLX, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(LLY, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(LRX, (float, int)): 
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(LRY, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(ULX, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(ULY, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(URX, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")
        if not isinstance(URY, (float, int)):
            raise ValueError("Input parameter for corner coordinates must be a number")

        self.ULX = ULX
        self.ULY = ULY
        self.LLX = LLX
        self.LLY = LLY
        self.LRX = LRX
        self.LRY = LRY
        self.URX = URX
        self.URY = URY

        logging.info("Searching for SAR from %s" % self.time.date().isoformat())

    def uncompress_zip(self, proclist):
        """ Uncompress infile if needed
        """
        sar_safe_list = []
        for infile in proclist:
            if os.path.isfile(infile):
                logging.debug("Uncompress if needed infile: %s" % (infile))
                tmpstr = infile.split("/")[-1]
                dstfile = "%s/%s.SAFE" % (RAWDIR, tmpstr.split(".")[0])
                logging.debug(dstfile)
                if not os.path.isdir(dstfile):
                    logging.debug("\nfile does not exists\n")
                    if infile.find(".zip") != -1:
                        cmd = "/usr/bin/unzip "+infile+" -d "+RAWDIR
                        logging.debug("\nStart uncompressing\n")
                        logging.debug(cmd)
                        subprocess.call(cmd, shell=True)
                        if os.path.isdir(dstfile):
                            sar_safe_list.append(dstfile)
                            os.remove(infile)

        self.sar_safe_list = sar_safe_list

    def get_NBS_ColhubData(self):
        ##################################################
        # Get todays Sentinel-1 data from NBS covering AOI
        # indir: Directory to store raw data localy
        # Returns a list of available products to be processed.
        ##################################################

        datestr = ("%04d%02d%02d" % (self.date.year, self.date.month, self.date.day))
        startDate = "%04d-%02d-%02dT02:00:00.000Z" % (self.date.year, self.date.month, self.date.day)
        stopDate = "%04d-%02d-%02dT09:30:59.999Z" % (self.date.year, self.date.month, self.date.day)

        ##################################################
        # Query relevant Sentinel-1 data from colhob.met.no
        # Returns a list of available products to be processed.
        ##################################################

        # timeliness = "NRT-3h"
        area = "%f %f,%f %f,%f %f,%f %f,%f %f" % (self.LLX, self.LLY,
                                                  self.LRX, self.LRY,
                                                  self.URX, self.URY,
                                                  self.ULX, self.ULY,
                                                  self.LLX, self.LLY)

        xmlFile = "%s/qres.xml" % (LOGDIR)

        cmd = "wget --no-check-certificate --user=%s --password=%s --output-document=%s " % (
            USER_NBS, PASSWD_NBS, xmlFile)
        cmd = cmd + "\"%ssearch?q=(beginPosition:[%s TO %s] AND endPosition:[%s TO %s]) " % (
            url, startDate, stopDate, startDate, stopDate)
        cmd = cmd + "AND %s AND %s " % (typ, mode)
        cmd = cmd + 'AND footprint:"Intersects(POLYGON((%s)))"&rows=100&start=0\' '  % (area)
        logging.debug(cmd)
        subprocess.call(cmd, shell=True)

        # Pars xmlFile to generate list of available data
        DOMTree = parse(xmlFile)
        collection = DOMTree.documentElement
        entrys = collection.getElementsByTagName("entry")
        proclist_tmp = []
        proclist_val = []

        for node in entrys:
            fname = "%s/%s.zip" % (
                RAWDIR, node.getElementsByTagName("title")[0].childNodes[0].nodeValue)
            fval = node.getElementsByTagName("link")[0].getAttribute("href").replace(
                "$value", "\\$value")
            if fname.find(datestr) > -1:
                proclist_tmp.append(fname)
                proclist_val.append(fval)

        # Parse the processedFile log and make a list of products to be downloaded
        processedFile = "%s/processedFile%s" % (LOGDIR, datestr)
        logging.debug(processedFile)
        processedLog = ""
        proclist = []
        if not os.path.isfile(processedFile):
            fid = open(processedFile, "w")
        else:
            fid = open(processedFile, "r+")
            processedLog = fid.read()

        for i in range(len(proclist_tmp)):
            # Only search for first part of the string. Similar files
            # may have different ending
            fsub = proclist_tmp[i].split("/")[-1][:30]
            val = proclist_val[i]

            if (processedLog.find(fsub) == -1):  # Check if file processed before
                if (str(proclist).find(fsub) == -1):  # Check if file already put to proclist ?
                    cmd = (
                        "wget --no-check-certificate --user=%s --password=%s "
                        "--output-document=%s " % (USER_NBS, PASSWD_NBS, proclist_tmp[i]))
                    cmd = cmd + '\"%s\" ' % (val)
                    subprocess.call(cmd, shell=True)
                    logging.debug(cmd)
                    proclist.append(proclist_tmp[i])
                    fid.write("%s," % (proclist_tmp[i]))
        fid.close()

        if len(proclist) > 0:
            self.uncompress_zip(proclist)
