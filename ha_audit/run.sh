#!/usr/bin/with-contenv bashio

bashio::log.info "Starting HA Audit v0.5.0"

python3 /audit.py

bashio::log.info "HA Audit finished"
