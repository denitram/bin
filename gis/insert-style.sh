#!/bin/bash

PROGNAME=insert-style.sh
WORKDIR=$1
USAGE="${PROGNAME} work_directory style_name"
STYLE=$2

if [ $# != 2 ]; then
  echo "Usage: $USAGE" >&2
  exit 1
fi

sed -i s/^layer\.style=$/layer\.style=${STYLE}/ ${WORKDIR}/*.gpd
