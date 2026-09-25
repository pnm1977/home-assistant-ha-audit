#!/usr/bin/with-contenv bashio

bashio::log.info "Starting HA Audit v0.5.0"

if ! python3 /audit.py; then
    bashio::log.error "System audit module failed"
fi

if ! python3 /config_scan.py; then
    bashio::log.error "Configuration inventory module failed"
fi

bashio::log.info "HA Audit finished"
