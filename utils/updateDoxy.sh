#!/bin/sh
DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$DIR"
export SSPAD_ROOT="$(dirname "$DIR")"
export SSPAD_VERSION=`cat $PRJ_ROOT/VERSION` 
exec doxygen sspad.doxyfile

