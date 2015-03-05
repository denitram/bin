#!/usr/bin/env python

# Publish datasets to geoserver
# - Scans a specific directory for "Geoserver Publish Data" (*.gpd) files
# - For each rasterdataset:
#     creates coveragestore
#     creates coverage (Geoserver automatically creates a layer)
#     set layer options (style)
#
# Assumptions:
# - all data will be published to one geoserver instance
# - all rasterdata within one directory will be published to one workspace
#   (prevents cross-links between data and workspaces)
# - data is available in the Geoserver instance (for grids: below the grid root directory
#   the directory structure is identical to the dir structure in the publish tree
#   (makes upload/ftp easy)
# - workspace exists in Geoserver

# In debug mode only api urls + commands + config data will be shown (verbose),
# no requests to the server will be made.
# Force debug mode (can be set on the commandline too)
DEBUG=False

import sys
import os
import glob
import urllib
import urllib2
import base64

# help tekst
if len(sys.argv) == 1:
  print """Usage: publish2geoserver.py <options>
Publishes coveragestores, coverages to Geoserver, and sets layeroptions. Updating existing
Geoserver objects is also possible.
 
Options (any order):
--process-dir=[dir]           directory to process (as subdirectory of current directory)
--file-filter=[pattern]       default: * (.gpd will always be appended)
--pub-stores                  publish the (raster) stores
--pub-coverages               publish the coverages (a basic layers will be created automatically)
--set-layeroptions            set the layer options
--update                      update existing Geoserver objects (stores, coverages, layers)
--no-proxy                    ignores proxy settings from the environment (http_proxy or internet
                              settings under Windows/Mac)
--debug                       if set: debugging mode, no request will be made to Geoserver,
                              verbose script output

Remarks:
1) When publishing a raster store, the data files do not have to be present in the .gpd directory,
   they will be referenced from within Geoserver, where they must be accessible at the location
   as specified in the .gpd file.
2) --set-layeroptions always performs an update (layers are auto-created by Geoserver).
3) Providing an empty password automatically enters debugging mode.
"""
  exit(0)

#########################################################
# Initialization (vars, commandline)
pubstores=False
pubcoverages=False
setlayeroptions=False
update=False
filefilter="*"
noproxy=False
reqlog=[]

for arg in sys.argv:
  # get commandline options (and optionally values)
  an = arg.split('=')[0]
  if len(arg.split('=')) > 1:
    av = arg.split('=')[1]

  # process commandline options
  # Directory to process
  if an == '--process-dir':
    processdirectory=av.strip('/')
  if an == '--pub-stores':
    pubstores=True
  if an == '--pub-coverages':
    pubcoverages=True
  if an == '--set-layeroptions':
    setlayeroptions=True
  if an == '--file-filter':
    filefilter=av
  if an == '--update':
    update=True
  if an == '--no-proxy':
    noproxy=True
  if an == '--debug':
    DEBUG=True

# ##########################
# Functions
def coveragestorexml(covstoreworkspace, covstorename, description, covstoretype, gridfile):
  return str.format("<coverageStore>\n\
  <name>{0}</name>\n\
  <description>{1}</description>\n\
  <type>{2}</type>\n\
  <enabled>true</enabled>\n\
  <workspace>\n\
    <name>{4}</name>\n\
  </workspace>\n\
  <__default>false</__default>\n\
  <url>file:{3}</url>\n\
</coverageStore>"
  , covstorename
  , description
  , covstoretype
  , gridfile
  , covstoreworkspace)

def coveragexml(covstorename, covname, covtitle, covdescription, keywords, abstract):
  keywordxml = ''
  for k in keywords.split(","):
    keywordxml = keywordxml + str.format("    <string>{0}</string>\n", k)
  keywordxml = keywordxml.strip()
  
  return str.format("<coverage>\n\
  <name>{0}</name>\n\
  <nativeName>{0}</nativeName>\n\
  <title>{1}</title>\n\
  <description>{2}</description>\n\
  <abstract>{5}</abstract>\n\
  <keywords>\n\
    <string>WCS</string>\n\
    {3}\n\
  </keywords>\n\
  <enabled>true</enabled>\n\
  <store class=\"coverageStore\">\n\
    <name>{4}</name>\n\
  </store>\n\
</coverage>"
  , covname
  , covtitle
  , covdescription
  , keywordxml
  , covstorename
  , abstract)

def coveragelayerxml(covname, defaultstyle):
  return str.format("<layer>\n\
  <name>{0}</name>\n\
  <type>RASTER</type>\n\
  <defaultStyle>\n\
    <name>{1}</name>\n\
  </defaultStyle>\n\
  <resource class=\"coverage\">\n\
    <name>{0}</name>\n\
  </resource>\n\
  <enabled>true</enabled>\n\
</layer>"
  , covname
  , defaultstyle)
  
# Set up the Add Coverage Store request
def addcoveragestore(covstoreworkspace, covstorename, description, covstoretype, gridfile):
  xml = coveragestorexml(covstoreworkspace, covstorename, description, covstoretype, gridfile)
  reqtype = ''
  if update:
    reqtype = 'PUT'
    apiurl = "/rest/workspaces/" + covstoreworkspace + "/coveragestores/" + covstorename + ".xml"
  else:
    reqtype = 'POST'
    apiurl = "/rest/workspaces/" + covstoreworkspace + "/coveragestores.xml"
  url = "http://" + geoserver_host + geoserver_instance + apiurl
  result = str(makerequest(url, xml, reqtype))
  print "Result: " + result
  reqlog.append('coveragestore ' + covstorename + ' ' + result)

def addcoverage(covstoreworkspace, covstorename, covname, covtitle, covdescription, keywords, abstract):
  xml = coveragexml(covstorename, covname, covtitle, covdescription, keywords, abstract)
  reqtype = ''
  if update:
    reqtype = 'PUT'
    apiurl = "/rest/workspaces/" + covstoreworkspace + "/coveragestores/" + covstorename + "/coverages/" + covname + ".xml"
  else:
    reqtype = 'POST'
    apiurl = "/rest/workspaces/" + covstoreworkspace + "/coveragestores/" + covstorename + "/coverages.xml"
  url = "http://" + geoserver_host + geoserver_instance + apiurl
  result = str(makerequest(url, xml, reqtype))
  print "Result: " + result
  reqlog.append('coverage ' + covname + ' ' + result)
  
def setcoveragelayeroptions(covstoreworkspace, covname, defaultstyle):
  xml = coveragelayerxml(covname, defaultstyle)
  apiurl = "/rest/layers/" + covstoreworkspace + ":" + covname + ".xml"
  url = "http://" + geoserver_host + geoserver_instance + apiurl
  result = str(makerequest(url, xml, 'PUT'))
  print "Result: " + result
  reqlog.append('layer ' + covname + ' ' + result)
  
# Make the HTTP request (POST, PUT, DELETE, GET)
def makerequest(url, xml, reqtype):
  respons = -1
  print "API URL   : ", url
  if DEBUG:
    print "Req Type  : ", reqtype
    print "Config XML: \n", xml
  else:
    base64string = base64.encodestring('%s:%s' % (geoserver_user, geoserver_password)).replace('\n', '')
    req = urllib2.Request(url)
    req.get_method = lambda: reqtype
    req.add_header("Authorization", "Basic %s" % base64string)
    req.add_header('Content-Type', 'application/xml')
    req.add_data(xml)
    try:
      if noproxy:
        uo = urllib2.build_opener(urllib2.ProxyHandler({})) 
        urllib2.install_opener(uo)
      resp = urllib2.urlopen(req)
      respons = resp.code
    except urllib2.URLError, e:
      respons = str(e)
  return respons
	
# Publish stores based on Geoserver Publish Data (.gpd)
def publishstores2geoserver(files):
  for f in MyFiles:
    # Read ze file and set variables
    print "Processing:", f
    gpdconfig = {}
    gpdconfig_file=open(f, 'r')
    for l in gpdconfig_file:
      if l.find("=") > 0:
       gpdconfig[l.split('=')[0]] = l.split('=')[1].strip()
    gpdconfig_file.close()

    if DEBUG:
      # Show the contents
      for c in gpdconfig:
        print c, ':', gpdconfig[c]
        
    # Add the coveragestore, should be possible using all known values
    addcoveragestore(gpdconfig['coveragestore.workspace']
      , gpdconfig['coveragestore.name']
      , gpdconfig['coveragestore.description']
      , gpdconfig['coveragestore.datatype']
      , coveragefile_rootdir + gpdconfig['coveragestore.filename']
      )

    print "\n"

# Publish coverages based on Geoserver Publish Data (.gpd)
def publishcoverages2geoserver(files):
  for f in MyFiles:
    # Read ze file and set variables
    print "Processing:", f
    gpdconfig = {}
    gpdconfig_file=open(f, 'r')
    for l in gpdconfig_file:
      if l.find("=") > 0:
       gpdconfig[l.split('=')[0]] = l.split('=')[1].strip()
    gpdconfig_file.close()

    if DEBUG:
      # Show the contents
      for c in gpdconfig:
        print c, ':', gpdconfig[c]

    # Add the coverage, should be possible using all known values
    addcoverage(gpdconfig['coveragestore.workspace']
      , gpdconfig['coverage.coveragestore.name']
      , gpdconfig['coverage.name']
      , gpdconfig['coverage.title']
      , gpdconfig['coverage.description']
      , gpdconfig['coverage.keywords']
      , gpdconfig['coverage.abstract']
      )

    print "\n"

# Publish coverages based on Geoserver Publish Data (.gpd)
def setcoveragelayeroptions2geoserver(files):
  for f in MyFiles:
    # Read ze file and set variables
    print "Processing:", f
    gpdconfig = {}
    gpdconfig_file=open(f, 'r')
    for l in gpdconfig_file:
      if l.find("=") > 0:
       gpdconfig[l.split('=')[0]] = l.split('=')[1].strip()
    gpdconfig_file.close()

    if DEBUG:
      # Show the contents
      for c in gpdconfig:
        print c, ':', gpdconfig[c]

    # Add the coverage, should be possible using all known values
    if len(gpdconfig['layer.style'].strip()) > 0:
      setcoveragelayeroptions(gpdconfig['coveragestore.workspace'], gpdconfig['layer.coverage.name'], gpdconfig['layer.style'])
    else:
      print "WARNING: no style information, skipping"

    print "\n"

# #####################################################################
# #####################################################################
# #####################################################################
# Ze script (MAIN)

# Geoserverinstance
# Read host config file (global)
config_file = open(processdirectory + '/config.session', "r")
hostconfig = {}
for l in config_file:
  if l.find("=") > 0:
    hostconfig[l.split('=')[0]] = l.split('=')[1].strip()
config_file.close()

geoserver_host=hostconfig['geoserver.host']
geoserver_instance=hostconfig['geoserver.instance']
geoserver_user=hostconfig['geoserver.user']
geoserver_password=raw_input(str.format("Geoserver password for {0} (empty=>debugging mode):", geoserver_user))
coveragefile_rootdir=(hostconfig['geoserver.coveragerootdir'])

if geoserver_password == "":
  DEBUG = True

# Print global settings
print "Debugging mode:       ", DEBUG
print "Process directory:    ", processdirectory
print "Geoserver host:       ", geoserver_host
print "Geoserver instance:   ", geoserver_instance
print "Geoserver user:       ", geoserver_user
print "Coverage file rootdir:", coveragefile_rootdir
if DEBUG:
  print "Geoserver password:   ", geoserver_password


# Get all files to process
MyFiles = glob.glob(processdirectory + "/" + filefilter + ".gpd")
if DEBUG:
  print "DEBUG: Files to process: "
  for f in MyFiles:
    print "  ", f

if pubstores:
  print "Publishing stores"
  publishstores2geoserver(MyFiles)

if pubcoverages:
  print "Publishing coverages"
  publishcoverages2geoserver(MyFiles)

if setlayeroptions:
  print "Setting layer options"
  setcoveragelayeroptions2geoserver(MyFiles)

print "Log:"
for e in reqlog:
  print e

print "\nDone."
