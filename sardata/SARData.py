# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import os, sys, subprocess
import numpy
from datetime import datetime, date
from xml.dom.minidom import parse

BINDIR = '/home/fou-fd-oper/software/sarwind/met-sar-vind/sarwind'

# Data paths
BASEDIR = '/lustre/storeA/project/fou/fd/project/sarwind'
RAWDIR = '%s/raw' % BASEDIR
TMPDIR = '%s/tmp' % BASEDIR
PNGDIR = '%s/png' % BASEDIR
NETCDFDIR = '%s/netcdf' % BASEDIR
LOGDIR = '%s/log' % BASEDIR
MODELDIR = '/lustre/storeB/project/metproduction/products/arome_arctic'



class GetSAR():
    """
    
    
    
    """
    
    def __init__(self,date_str=)
def getColhubData(indir, NRT):
    ##################################################
    # Get todays Sentinel-1 data from NBS covering AOI
    # indir: Directory to store raw data localy
    # Returns a list of available products to be processed.
    ##################################################
    now = datetime.now()
    yyyy = now.year
    mm = now.month
    dd = now.day
    if NRT == 0:
        yyyy = 2022
        mm = 10
        dd = 5

    datestr =("%04d%02d%02d"%(yyyy,mm,dd))
    startDate = '%04d-%02d-%02dT02:00:00.000Z' % (yyyy,mm,dd)
    stopDate = '%04d-%02d-%02dT09:30:59.999Z' % (yyyy,mm,dd)

    ##################################################
    # Query relevant Sentinel-1 data from colhob.met.no
    # Returns a list of available products to be processed.
    ##################################################
    url = 'https://colhub.met.no/'
    typ = 'GRD'
    mode = 'EW'

    timeliness = 'NRT-3h'
    area = '-19.7 63.8, 70.0 63.8, 70.0 82.3, -19.7 82.3, -19.7 63.8'
    xmlFile = '%s/qres.xml' % (LOGDIR)

    cmd = 'wget --no-check-certificate --user=frode.dinessen --password=n:kC0Q5H --output-document=%s ' % (xmlFile)
    cmd = cmd + '\'%ssearch?q=(beginPosition:[%s TO %s] AND endPosition:[%s TO %s]) ' % (url,startDate,stopDate,startDate,stopDate)
    cmd = cmd + 'AND %s AND %s ' % (typ,mode)
    cmd = cmd + 'AND footprint:"Intersects(POLYGON((%s)))"&rows=100&start=0\' '  % (area)
    print(cmd)
    subprocess.call(cmd, shell=True)

    # Pars xmlFile to generate list of available data
    DOMTree = parse(xmlFile)
    collection = DOMTree.documentElement
    entrys = collection.getElementsByTagName("entry")
    proclist_tmp = []
    proclist_val = []

    for node in entrys:
        fname = '%s/%s.zip' % (indir,node.getElementsByTagName('title')[0].childNodes[0].nodeValue  )
        fval = node.getElementsByTagName("link")[0].getAttribute('href').replace('$value','\$value')
        if fname.find(datestr) > -1:
           proclist_tmp.append(fname)
           proclist_val.append(fval)

    # Pars the processedFile log and make a list of products to be downloaded
    processedFile = '%s/processedFile%s' % (LOGDIR,datestr)
    print (processedFile)
    processedLog = ''
    proclist = []
    if os.path.isfile(processedFile) == False:
        fid=open(processedFile,'w')
    else:
        fid = open(processedFile, 'r+')
        processedLog = fid.read()

    for i in range(len(proclist_tmp)):
        #Only search for first part of the string. Simmilar files may have diffrent ending
        fsub = proclist_tmp[i].split('/')[-1][:30]
        val = proclist_val[i]

        if (processedLog.find(fsub) == -1): #Check if file processed before
            if (str(proclist).find(fsub) == -1): #Check if file already put to proclist ?
                cmd = 'wget --no-check-certificate --user=frode.dinessen --password=n:kC0Q5H --output-document=%s ' % (proclist_tmp[i])
                cmd = cmd + '\"%s\" ' % (val)
                subprocess.call(cmd, shell=True)
                print (cmd)
                proclist.append(proclist_tmp[i])
                fid.write('%s,' % (proclist_tmp[i]))
    fid.close()

    return proclist


def uncompress_zip(infile):
    ###############################################
    # Uncumpress infile if needed
    ###############################################
    print('\n########################################################')
    print('## Uncompress if needed infile: %s' % (infile))
    tmpstr = infile.split('/')[-1]
    dstfile = '%s/%s.SAFE' % (RAWDIR,tmpstr.split('.')[0])
    print(dstfile)
    if os.path.isdir(dstfile) == False:
        print('\nfile does not exists\n')
        if infile.find('.zip') != -1:
            cmd = '/usr/bin/unzip '+infile+' -d '+RAWDIR
            print('\nStart uncompressing\n')
            print(cmd)
            subprocess.call(cmd, shell=True)
            if os.path.isdir(dstfile) == False:
                    print('Error unzipping file %s' % (infile))
                    sys.exit()
            os.remove(infile)
        else:
            print('Error: Not able to extract SAFE catalouge')
            sys.exit()

    return dstfile

