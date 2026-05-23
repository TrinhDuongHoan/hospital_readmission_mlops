#!/bin/bash

set -a
source .env
set +a

python kafka/producer.py