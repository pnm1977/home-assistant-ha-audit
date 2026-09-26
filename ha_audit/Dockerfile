FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

ENV HA_AUDIT_VERSION=${BUILD_VERSION}

RUN apk add --no-cache \
    python3 \
    py3-requests \
    py3-websocket-client \
    py3-yaml

COPY run.sh /
COPY audit.py /
COPY config_scan.py /
COPY quality_scan.py /
COPY not_provided_reference_scan.py /

RUN chmod a+x /run.sh

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

CMD ["/run.sh"]
