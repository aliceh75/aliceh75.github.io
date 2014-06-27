#!/bin/bash

if [ $# -ne 1 ]
  then
    echo "Usage: $0 <commit message>"
    exit 1
fi

ghp-import -m "$1" -p -b master output-live/
