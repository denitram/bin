#!/usr/bin/env python

# Generates Geoserver publish data files (.gpd)
# .gpd files are used by publish2geoserver.py to automatically publish
# many coverage stores, coverages, layers and/or featurelayers (in progress)
# to a specific Geoserver instance.

# The tool only generates a basic service, with common default settings.
# Some settings can be adjusted by editing the generated files, it is also
# possible to use an interactive mode. A bit of logic is built in:
# Empty coverage descriptions will be copied from the abstract.

# Global settings
# - all data will be published to one geoserver instance
# - all rasterdata within one directory will be published to one workspace; you may actually
#   alter the .gpd files to change this behaviour, but that's not recommended because the default
#   prevents cross-links between data and workspaces.

# In debug mode no files will be written, verbose screen output.
# Force debug mode (can be set on the commandline too)
DEBUG=False

import sys
import os
import glob

# help tekst
if len(sys.argv) == 1:
  print """Usage: generate-geoserverpublishdata.py <options>
Generates .gpd files alongside the (raster) source files.

Options (any order):
--process-dir=[dir]                       directory to process (as subdirectory of current directory)
--file-filter=[pattern]                   default: *.*
--strip-name=[pattern,pattern,...]        multiple patterns to remove from filename (no spaces allowed)
--covstore-key=[key]                      key (string) to add in front of coveragestore name
--coverage-key=[key]                      key (string) to add in front of coverage name
--workspace=[geoserver_workspace]         name of workspace to add coveragestores (must exist)
--interactive                             interactive mode: asks info for individual coverages
--set-param=[key]                         set only information for key (in .gpd), see remark 4
--show-param=[key]                        show only information for key (in .gpd), see remark 4
--update-param=[key]                      update information for specified key (in .gpd), see remark 4
--update-value=[value]                    the value to update, see remark 5
--debug                                   if set: debugging mode, no files will be written, verbose

Remarks:
1) The script will ask for the global settings, even in non-interactive mode.
2) Defaults will be showed within [] for each option, they can be accepted by hitting <enter>.
   A new value can be entered, example:
     Coverage title (displayed) [auto_title]: mytitle
   Appending to a value is possible by entering a plus sign (+) followed by the desired text. Example:
     Coverage keywords [environment]: +,health
     In this case: mind the , before the next keyword!
3) Default values will be read from an existing .gpd file, the directory (session) specific defaults, or
   the global (script directory) defaults (in this order); exception: the (hidden) description will be
   copied from the coverage abstract in interactive mode (otherwise the global default).
4) Available keys:
     coveragestore.workspace
     coveragestore.description
     coverage.title
     coverage.description
     coverage.abstract
     coverage.keywords
     layer.style
5) While updating a specified key, it is possible to specify the name of another key to extract data
   from, use a semi-colon in front of the key, e.g.:
   --update-param=coverage.description --update-value=:coverage.abstract
"""
  exit(0)

#########################################################
# Initialization (vars, commandline)
stripfromfilename=''
coveragestore_key=''
coverage_key=''
coverage_keywords=''
filefilter="*"
interactive=False
showparam=""
setparam=""
updateparam=""
updatevalue=""

for arg in sys.argv:
  # get commandline options (and optionally values)
  an = arg.split('=')[0]
  if len(arg.split('=')) > 1:
    av = arg.split('=')[1]

  # process commandline options
  if an == '--process-dir':
    processdirectory=av.strip('/')
  if an == '--strip-name':
    stripfromfilename=av.split(',')
  if an == '--covstore-key':
    coveragestore_key=av
  if an == '--coverage-key':
    coverage_key=av
  if an == '--file-filter':
    filefilter=av
  if an == '--workspace':
    coveragestore_workspace=av
  if an == '--interactive':
    interactive=True
  if an == '--show-param':
    showparam=av
  if an == '--set-param':
    setparam=av
  if an == '--update-param':
    updateparam=av
  if an == '--update-value':
    updatevalue=av
  if an == '--debug':
    DEBUG=True

#########################################################
# Configuration helper functions
# Get config parameters
# 1. existing .gpd file
# 2. session value from process-dir defaults
# 3. default value from script dir defaults
def getconfigparam(param):
  if param in gpdconfig:
    return gpdconfig[param]
  elif param in sessionconfig:
    return sessionconfig[param]
  elif param in defaultconfig:
    return defaultconfig[param]
  else:
    return ""
  
# Config file loader
def loadconfigfile(configfile):
  if os.path.exists(configfile):
    config_file = open(configfile, "r")
    currentconfig = {}
    for l in config_file:
      if l.find("=") > 0:
	    currentconfig[l.split('=')[0]] = l.split('=')[1].strip()
    config_file.close()
    return currentconfig
  else:
    return {}

# Get user input
def getuserinput(prompt, param):
  currentvalue = str(getconfigparam(param).strip())
  if currentvalue == "":
    currentvalue = param
  i = raw_input(prompt + " [" + str(currentvalue) + "]: ").strip()
  if len(i) > 0:
    if (i).startswith('+'):
      return currentvalue + str(i)[1:]
    else:
      return i
  else:
    return currentvalue

GPD_CONTENT = ""
def addtogpd(datarow):
  global GPD_CONTENT
  if DEBUG:
    print datarow
  else:
    GPD_CONTENT = GPD_CONTENT + datarow + "\n"

############################################################	
# Generate Geoserver Publish Data (.gpd)
# Loop through the data files, generate
def genrasterpublishfiles(files):
  global gpdconfig  # test files (type, name)
  global GPD_CONTENT

  for f in MyFiles:
    GPD_CONTENT = ""
    fileext = os.path.splitext(f.lower())[1]
    filename = os.path.basename(f)
    # gridstore_type (extension)
    if fileext == '.asc':
      coveragestore_type="ArcGrid"
    elif fileext == '.tif':
      coveragestore_type="GeoTIFF"
    elif fileext == '.tiff':
      coveragestore_type="GeoTIFF"
    else:
      coveragestore_type="UNKNOWN"

    if coveragestore_type!="UNKNOWN":
      if f.find(' ') > 0:
        print "WARNING: Spaces found in coverage filename, skipping:", filename
      else:
        print "Processing:", filename, coveragestore_type
      
        # Generate coveragestorename and coverage name (will always be reset, no user input)
        # write a default .gpd file, empty fields can be filled out by the user
        # specified sets of characters can be stripped from the filename
        # Get name without extension
        f2 = filename.split(".")[0]
        # Strip specified stuff
        for s in stripfromfilename:
          f2 = f2.replace(s,'').lower().strip("_")
        # Prepend keys
        coveragestore_name = (coveragestore_key + '_' + f2).strip("_")
        coverage_name = (coverage_key + '_' + f2).strip("_")

        # Print settings
        print "  Clean filename:", f2
        print "  CoverageStore name:", coveragestore_name
        print "  Service/coverage name:", coverage_name
        print "  Raster source file name:", f

        # Load an existing configuration
        publish_file = processdirectory + "/" + filename.split(".")[0] + ".gpd"
        gpdconfig = loadconfigfile(publish_file)
        print "  Geoserver Publish Data filename (.gpd):", publish_file

        # In interactive mode, ask for some information (except globals and servicenames)
        if getconfigparam('coverage.title') == '':
          gpdconfig['coverage.title'] = coverage_name
        if interactive:
          coveragestore_description = getuserinput('  CoverageStore description', 'coveragestore.description')
          coverage_title = getuserinput('  Coverage title (displayed)', 'coverage.title')
          coverage_abstract = getuserinput('  Coverage abstract (displayed)', 'coverage.abstract')
          if 'coverage.description' in gpdconfig:
            coverage_description = gpdconfig['coverage.description']
          else:
            coverage_description = coverage_abstract
          coverage_description = getuserinput('  Coverage description (HIDDEN)', coverage_description)
          coverage_keywords = getuserinput('  Coverage keywords (, separated)', 'coverage.keywords')
          layer_style = getuserinput('  Coverage/layer style (sld)', 'layer.style')
        else:
          coveragestore_description = getconfigparam('coveragestore.description')
          coverage_title = getconfigparam('coverage.title')
          coverage_description = getconfigparam('coverage.description')
          coverage_abstract = getconfigparam('coverage.abstract')
          coverage_keywords = getconfigparam('coverage.keywords')
          layer_style = ""
        
        print "Generating Geoserver Publish Data: ", publish_file
        addtogpd("coveragestore.workspace=" + coveragestore_workspace)
        addtogpd("coveragestore.datatype=" + coveragestore_type)
        addtogpd("coveragestore.filename=" + f )
        addtogpd("coveragestore.name=" + coveragestore_name)
        addtogpd("coveragestore.description=" + coveragestore_description)
        addtogpd("coverage.coveragestore.name=" + coveragestore_name)
        addtogpd("coverage.name=" + coverage_name)
        addtogpd("coverage.title=" + coverage_title)
        addtogpd("coverage.description=" + coverage_description)
        addtogpd("coverage.abstract=" + coverage_abstract)
        addtogpd("coverage.keywords=" + coverage_keywords.replace(' ',''))
        addtogpd("layer.coverage.name=" + coverage_name)
        addtogpd("layer.style=" + layer_style)

        if DEBUG:
          print "\n" + GPD_CONTENT
        else:
          print "Writing .gpd file"
          gpd = open(publish_file, 'w')
          gpd.write(GPD_CONTENT)
          gpd.close()

# Show parameters
def showgpdparam(files, param):
  for f in MyFiles:
    filename = os.path.basename(f)
    publish_file = processdirectory + "/" + filename.split(".")[0] + ".gpd"
    gpdconfig = loadconfigfile(publish_file)
    print publish_file.ljust(60, ' '), gpdconfig[param]

# Set parameters
def setgpdparam(files, param):
  for f in MyFiles:
    filename = os.path.basename(f)
    publish_file = processdirectory + "/" + filename.split(".")[0] + ".gpd"
    gpdconfig = loadconfigfile(publish_file)
    print "file: " + publish_file
    newvalue = raw_input(param + " [" + gpdconfig[param] +"]: ").strip()
    if newvalue != "":
      gpdconfig[param] = newvalue
    if DEBUG:
      for p in gpdconfig:
        print p + "=" + gpdconfig[p]
    else:
      print param + "=" + gpdconfig[param]
      # Write out new file
      print "Writing .gpd file"
      gpd = open(publish_file, 'w')
      for p in gpdconfig:
        gpd.write(p + "=" + gpdconfig[p] + "\n")
      gpd.close()

    print "\n"

# Update parameters (bulk)
def updategpdparam(files, param, value):
  for f in MyFiles:
    filename = os.path.basename(f)
    publish_file = processdirectory + "/" + filename.split(".")[0] + ".gpd"
    gpdconfig = loadconfigfile(publish_file)
    print "file: " + publish_file
    if value[0] == ":":
      value2 = gpdconfig[value[1:]]
    else:
      value2 = value
    gpdconfig[param] = value2
    if DEBUG:
      for p in gpdconfig:
        print p + "=" + gpdconfig[p]
    else:
      print param + "=" + gpdconfig[param]
      # Write out new file
      print "Writing .gpd file"
      gpd = open(publish_file, 'w')
      for p in gpdconfig:
        gpd.write(p + "=" + gpdconfig[p] + "\n")
      gpd.close()

    print "\n"
  
# #####################################################################
# #####################        MAIN                  ##################
# #####################################################################

# Ze script, pretty minimal :-)
# Get all existing configurations
defaultconfig = loadconfigfile('config.default')
sessionconfig = loadconfigfile(processdirectory + '/config.session')
gpdconfig = {} # empty at the moment


##########################################################
# Coveragestore base description
# Ask user for descriptions (should be read from XML metadata file, if present)
# Only if not in parameter specific mode
if setparam == "" and showparam == "" and updateparam == "":
  print "Enter GLOBAL/DEFAULT settings"
  print "Just hit <enter> to accept an existing default.\n"
  print "GLOBAL: Store and layer configuration values"
  coveragestore_description = getuserinput('  CoverageStore description', 'coveragestore.description')
  coverage_abstract = getuserinput('  Coverage abstract (displayed)', 'coverage.abstract')
  if getconfigparam('coverage.description') == "":
    coverage_description = coverage_abstract
  else:
    coverage_description = getconfigparam('coverage.description')
  coverage_description = getuserinput('  Coverage description (HIDDEN)', coverage_description)
  coverage_keywords = getuserinput('  Coverage keywords (, separated)', 'coverage.keywords').replace(' ', '').strip()
  print "\nGLOBAL: Deploy to the following geoserver host:"
  geoserver_host=getuserinput('  Geoserver host url', 'geoserver.host')
  geoserver_instance=getuserinput('  Geoserver instance', 'geoserver.instance')
  geoserver_user=getuserinput('  Geoserver admin user', 'geoserver.user')
  coveragefile_rootdir=getuserinput('  Geoserver coveragerootdir (empty, or with trailing slash)', '')
  coveragefile_rootdir=coveragefile_rootdir

  # Save global description settings for future sessions
  config_file=open(processdirectory + "/config.session", "w")
  config_file.write("coveragestore.description=" + coveragestore_description + "\n")
  config_file.write("coverage.description=" + coverage_description + "\n")
  config_file.write("coverage.abstract=" + coverage_abstract + "\n")
  config_file.write("coverage.keywords=" + coverage_keywords + "\n")
  config_file.write("geoserver.host=" + geoserver_host + "\n")
  config_file.write("geoserver.instance=" + geoserver_instance + "\n")
  config_file.write("geoserver.user=" + geoserver_user + "\n")
  config_file.write("geoserver.coveragerootdir=" + coveragefile_rootdir + "\n")
  config_file.close()

  # Reload session config with updated values
  sessionconfig = loadconfigfile(processdirectory + '/config.session')

  #########################################################
  # Print global settings
  print "Debugging mode:             ", DEBUG
  print "Process directory:          ", processdirectory
  print "Strip from filename:        ", str(stripfromfilename)
  print "Coveragestore key (prefix): ", coveragestore_key
  print "Coveragestore description:  ", coveragestore_description
  print "Coverage key (prefix):      ", coverage_key
  print "Coverage keywords:          ", coverage_keywords
  print "Coverage description:       ", coverage_description
  print "Coverage abstract:          ", coverage_abstract
  print "Geoserver workspace:        ", coveragestore_workspace
  print "Geoserver host:             ", geoserver_host
  print "Geoserver instance:         ", geoserver_instance
  print "Geoserver user:             ", geoserver_user
  print "Geoserver coveragefile root:", coveragefile_rootdir
  print "\n"

# Start with ze file names
if showparam != "" or setparam != "" or updateparam != "":
  filefilter = filefilter + ".gpd"
if DEBUG:
  print filefilter
MyFiles = glob.glob(processdirectory + "/" + filefilter)
if DEBUG:
  print "DEBUG: Files to process: "
  for f in MyFiles:
    print "  ", f

# Zen, zjenerate the .gpd files
if showparam != "":
  showgpdparam(MyFiles, showparam)
elif setparam != "":
  setgpdparam(MyFiles, setparam)
elif updateparam != "":
  updategpdparam(MyFiles, updateparam, updatevalue)
else:
  genrasterpublishfiles(MyFiles)

