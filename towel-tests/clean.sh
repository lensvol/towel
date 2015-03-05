#! /bin/bash

PROJ_DIR=/home/ina/projects/glance
TEST_DB=/tmp/tests.sqlite

# remove test db
rm -rf "$TEST_DB"

# FIXME damn damn bad, have to find a way to kill PRECISELY the server launched
kill -TERM -$(pgrep -f artifacts)
