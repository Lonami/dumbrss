#!/bin/bash

DIRNAME=`dirname "$0"`

[[ -d $DIRNAME/venv ]] && source $DIRNAME/venv/bin/activate
$DIRNAME/dumbrss.py fetch

