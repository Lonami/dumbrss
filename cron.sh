#!/bin/bash

DIRNAME=`dirname "$0"`

source $DIRNAME/venv/bin/activate
$DIRNAME/dumbrss.py fetch

