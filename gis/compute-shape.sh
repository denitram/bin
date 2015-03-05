#!/bin/bash -x

### Variables
PRGNAM="compute-shape.sh"
USAGE="Use: ${PRGNAM} \"directory\""
DIR=${1}
DANK_SHAPE=/home/martine/data/projects/dank/data/shape
WORKING_DIR=${DANK_SHAPE}/${DIR}

### DB VARIABLES
DB_HOST=pgl02-ext-p.rivm.nl
DB_NAME=dank_test
USER=dank
PASSWORD=nothx4db#
### Local postgreql
#DB_HOST=localhost

### Geoserver variables
GEO_HOST=geosl03-ext-t.rivm.nl
GEOADM=geosadmin
#PASSWDADM=:b1c3sdkle#01
### Geoserver localhost
#GEO_HOST=localhost
#GEOADM=geoadmin
PASSWDADM=afblijven!

if [ $# != 1 ]; then
  echo "$USAGE" >&2
  exit 1
fi

cd ${WORKING_DIR}

CSV_FILE="`ls *.csv`"
SHP="`ls *.shp`"
SHAPE_FILE=$SHP
SLD_FILE="`ls *.sld`"

#echo ${CSV_FILE} 
#echo ${SHP} 
#echo ${SLD_FILE} 

re='(.*)+(_)[0-9]+(.*)+(\.shp)'
while [[ $SHP =~ $re ]]; do
  SHP=${BASH_REMATCH[1]}${BASH_REMATCH[3]}
done

LAYER_NAME=$SHP
TABLE_NAME=$LAYER_NAME
VIEW_NAME=$TABLE_NAME
STYLE_NAME=$LAYER_NAME

#echo "Shape file: $SHAPE_FILE"
#echo "Layer name: $LAYER_NAME"
#echo "View name: $VIEW_NAME"

#### DB functions
create_db_table()
{
if (ogrinfo "$SHAPE_FILE" |grep -i point)
then
  ogr2ogr -overwrite -a_srs "EPSG:28992" -f "PostgreSQL" PG:"host=$DB_HOST dbname=$DB_NAME user=$USER password=$PASSWORD" $SHAPE_FILE -lco "GEOMETRY_NAME=geom" -nlt Point -nln dank.$TABLE_NAME
elif (ogrinfo "$SHAPE_FILE" |grep -i polygon)
then
  ogr2ogr -overwrite -a_srs "EPSG:28992" -f "PostgreSQL" PG:"host=$DB_HOST dbname=$DB_NAME user=$USER password=$PASSWORD" $SHAPE_FILE -lco "GEOMETRY_NAME=geom" -nlt MultiPolygon -nln dank.$TABLE_NAME
fi
 }
 
create_db_view()
{
  psql -h $DB_HOST -U $USER $DB_NAME -c "create view dank_pub.vw_$VIEW_NAME as select * from dank.$TABLE_NAME;"
}

grant_ro()
{
  psql -h $DB_HOST -U $USER $DB_NAME -c "grant select on table dank_pub.vw_$LAYER_NAME to dank_pub_ro;"
}

populate_geo()
{
  psql -h $DB_HOST -U $USER $DB_NAME -c "select populate_geometry_columns();"
}

### Geoserver functions
reload_geo_conf()
{
  curl -v -u $GEOADM:$PASSWDADM -XPOST  http://$GEO_HOST:8080/geoserver/rest/reload
}

create_style()
{
  curl -v -u $GEOADM:$PASSWDADM -XPOST -H "Content-type: text/xml" -d "<style><name>$STYLE_NAME</name><filename>$SLD_FILE</filename></style>" http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/styles
} 

update_style()
{
  curl -v -u $GEOADM:$PASSWDADM -XPUT -H "Content-type: application/vnd.ogc.se+xml" -d @${SLD_FILE} http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/styles/$STYLE_NAME
}

create_layer()
{
  TITLE=`grep titel $CSV_FILE | cut -d ";" -f 2`
  ABSTRACT=`grep samenvatting $CSV_FILE | cut -d ";" -f 2`
  METALINK=`grep metadatalink $CSV_FILE | cut -d ";" -f 2`
  #curl -v -u $GEOADM:$PASSWDADM -XPUT -H "Content-type: text/xml" -d "<featureType><title>$TITLE</title><abstract>$ABSTRACT</abstract><metadataLinks><metadataLink><type>text/plain</type><metadataType>ISO19115:2003</metadataType><content>$METALINK</content></metadataLink></metadataLinks></featureType>" http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/datastores/pg_dank/featuretypes
  #curl -v -u $GEOADM:$PASSWDADM -XPOST -H "Content-type: text/xml" -d "<featureType><name>$LAYER_NAME</name><nativeName>vw_$VIEW_NAME</nativeName><title>$TITLE</title><abstract>$ABSTRACT</abstract><metadataLink><content>$METALINK</content></metadataLink></featureType>" http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/datastores/pg_dank/featuretypes
  curl -v -u $GEOADM:$PASSWDADM -XPOST -H "Content-type: text/xml" -d "<featureType><name>$LAYER_NAME</name><nativeName>vw_$VIEW_NAME</nativeName><title>$TITLE</title><abstract>$ABSTRACT</abstract></featureType>" http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/datastores/pg_dank/featuretypes
}

update_layer()
{
  TITLE=`grep titel $CSV_FILE | cut -d ";" -f 2`
  ABSTRACT=`grep samenvatting $CSV_FILE | cut -d ";" -f 2`
  METALINK=`grep metadatalink $CSV_FILE | cut -d ";" -f 2`
  curl -v -u $GEOADM:$PASSWDADM -XPUT -H "Content-type: text/xml" -d "<featureType><title>$TITLE</title><abstract>$ABSTRACT</abstract><metadataLinks><metadataLink><type>text/plain</type><metadataType>ISO19115:2003</metadataType><content>$METALINK</content></metadataLink></metadataLinks></featureType>" http://$GEO_HOST:8080/geoserver/rest/workspaces/dank/datastores/pg_dank/featuretypes
}

assign_style()
{
  curl -u $GEOADM:$PASSWDADM -XPUT -H "Content-type: text/xml" -d "<layer><defaultStyle><name>$STYLE_NAME</name><workspace>dank</workspace></defaultStyle></layer>" http://$GEO_HOST:8080/geoserver/rest/layers/dank:$LAYER_NAME
}

enable_layer()
{
  curl -v -u $GEOADM:$PASSWDADM -XPUT -H "Content-type: text/xml" -d "<layer><name>$LAYER_NAME</name><enabled>true</enabled></layer>"  http://$GEO_HOST:8080/geoserver/rest/layers/dank:$LAYER_NAME.xml
}

### Help functions
convert_csv(){
if (file "$CSV_FILE" |grep -i ISO-8859)
then
  cp $CSV_FILE $CSV_FILE-ORG
  iconv --from-code=ISO-8859-1 --to-code=UTF-8 $CSV_FILE-ORG --output $CSV_FILE
fi
}

is_csv(){
  [ -n "$CSV_FILE" ]
}

is_shape(){
  [ -n "$SHP" ]
}

is_sld(){
  [ -n "$SLD_FILE" ]
}

is_view(){
  [ -n "$VIEW_NAME" ]
}

is_geom_point(){
  [ ogrinfo "$SHP" | grep -i 'point']
}

#### main

convert_csv
create_layer
assign_style
enable_layer

exit

##############################

if is_shape
then
  create_db_table
  echo "### TABLE created"
else
  echo "*** No shape file found"
  exit
fi

if is_view
then
  create_db_view
  echo "### VIEW created"
else
  echo "*** No view's name found"
  exit
fi

grant_ro
populate_geo

reload_geo_conf

if is_sld
then
  create_style
  update_style
  echo "### STYLE created"
else
  echo "*** No SLD file found"
  exit
fi

#exit

convert_csv
create_layer
assign_style
enable_layer
