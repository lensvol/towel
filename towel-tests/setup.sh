#! /bin/bash

TEST_SRC_DIR=`pwd`
PROJ_DIR=/home/ina/projects/glance
CONFIG_FILE="$PROJ_DIR/etc/glance-artifacts.conf"

bash "$PROJ_DIR/tools/with_venv.sh" python "$TEST_SRC_DIR/towel-tests/start_server.py" --config-file $CONFIG_FILE &

# create test_db
bash "$PROJ_DIR/tools/with_venv.sh" python -m "glance.cmd.manage" --config-file $CONFIG_FILE db_sync
