#!/usr/bin/env python
# -*- coding: utf-8 -*-

DEBUG=False

import sys
import os
import glob
import csv
import re


if len(sys.argv) < 2:
	print "Usage: generate-dankpublishdata.py filename.csv"
	exit(0)


# Search the .cvs files
cssfilter = "*.csv"
shpfilter = "*.shp"
sldfilter = "*.sld"
processdirectory = "."
MyCsvFiles = glob.glob(processdirectory + "/" + cssfilter)
MyShpFile = glob.glob(processdirectory + "/" + shpfilter)
MysldFile = glob.glob(processdirectory + "/" + sldfilter)

for f in MyCsvFiles:
	csvFilename = os.path.basename(f)

	with open(csvFilename) as csvfile:
	 	input_csv = csv.reader(csvfile, delimiter=';')
	 	for row in input_csv:
			if row[0] == 'bestandsnaam':	
				coverage_filename = row[1]
			if row[0] == 'versie':
				coverage_version = row[1]
			if row[0] == 'bronhouder':
				coverage_bronhouder = row[1]
			if row[0] == 'titel':	
				coverage_title = row[1]
			if row[0] == 'thema':	
				coverage_thema = row[1]
			if row[0] == 'afkorting':
				coverage_afkorting = row[1]
			if row[0] == 'samenvatting':
				coverage_abstract = row[1]
			if row[0] == 'thematype':
				coverage_thematype = row[1]
			if row[0] == 'geometry':
				coverage_geometry = row[1]
			if row[0] == 'metadatalink':
				coverage_metadatalink = row[1]
			if row[0] == 'maxschaal':
				coverage_maxschaal = row[1]
			if row[0] == 'minschaal':
				coverage_minschaal = row[1]

	#  csvfile.close()

	print "coverage_filename is: %s" % coverage_filename
	print "Titel is: %s" % coverage_title
	print "Versie is: %s" % coverage_version

#######################################################
	tifFile = csvFilename.replace('.csv', '.tif')
	print "TIFF file: ", tifFile

# f = "altr_a01_20141113_gv_potnatbestui-20141117.tif"
# fileext = os.path.splitext(f.lower())[1]
# filename = os.path.basename(f)
	f1 = tifFile.split(".")[0]
	# f3 = f1.replace("tif", '').lower().strip("_")
	f2 = f1.split("-")[0]
	# f3 = f2.split("_\8d")
	f3 = re.sub("_\d\d\d\d\d\d\d\d","",f2)


# print "fileext is: %s" % fileext # .tif
# print "filename is: %s" %filename # altr_a01_20141113_gv_potnatbestui-20141117.tif
	print "f1 is: %s" % f1 # altr_a01_20141113_gv_potnatbestui-20141117
	print "f3 is: %s" % f3 # altr_a01_20141113_gv_potnatbestui-20141117
	print "f2 is: %s" % f2 # altr_a01_20141113_gv_potnatbestui
	print "f3 is: %s" % f3 # altr_a01gv_potnatbestui

if len(f1) > 0:
	exìt(0)
#######################################################
# DANK vars
coveragestore_type = "GeoTIFF"
coveragestore_workspace = "dank"
coverage_description = "Generated with GeoTIFF"

coveragestore_name = f1
coverage_name = f3
layer_style = coverage_name

print "Coveragestore name: %s" % coveragestore_name
print "Coverage name: %s" % coverage_name
print "Coverage description: %s" % coverage_description
print "Coverage abstract: %s" % coverage_abstract
print "Layer style: %s" % layer_style

############################################################    
# Generate Geoserver Publish Data (.gpd)
# Loop through the data files, generate
def genrasterpublishfiles(files):
    global gpdconfig  # test files (type, name)
    global GPD_CONTENT

    GPD_CONTENT = ""
    fileext = os.path.splitext(f.lower())[1]
    filename = os.path.basename(f)
    # gridstore_type (extension)
    coveragestore_type="GeoTIFF"
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


