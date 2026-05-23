#!/bin/bash

kafka-topics \
  --bootstrap-server kafka:9092 \
  --create \
  --if-not-exists \
  --topic patient-events \
  --partitions 3 \
  --replication-factor 1

kafka-topics \
  --bootstrap-server kafka:9092 \
  --create \
  --if-not-exists \
  --topic prediction-results \
  --partitions 3 \
  --replication-factor 1

kafka-topics \
  --bootstrap-server kafka:9092 \
  --list