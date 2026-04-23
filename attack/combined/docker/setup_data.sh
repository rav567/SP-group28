#!/bin/bash
# populates /opt/hospital-data/ from pre-copied datasets based on SERVER_ROLE

mkdir -p /opt/hospital-data

if [ "$SERVER_ROLE" = "ehr" ]; then
    cp /opt/ehr_data/* /opt/hospital-data/
elif [ "$SERVER_ROLE" = "iot" ]; then
    cp /opt/iot_data/* /opt/hospital-data/
elif [ "$SERVER_ROLE" = "portal" ]; then
    cp /opt/portal_data/* /opt/hospital-data/
fi

chown -R ehradmin:ehradmin /opt/hospital-data
echo "[setup_data] $SERVER_ROLE data populated in /opt/hospital-data/"
