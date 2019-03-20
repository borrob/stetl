#!/bin/bash
#
# Shortcut to run all basic examples with the Stetl Docker image.
#

for dir in `echo [0-9]*`; do
	pushd $dir
	echo "==== running etl.sh for $dir ===="
	export WORK_DIR=$(pwd)
	docker run -v ${WORK_DIR}:${WORK_DIR} -w ${WORK_DIR} geopython/stetl:2.0 stetl -c etl.cfg
	popd
done
