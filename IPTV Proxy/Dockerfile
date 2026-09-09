# syntax=docker/dockerfile:1.7
FROM alpine:3.21 AS binary

ARG TARGETARCH
ARG TARGETVARIANT

COPY iptv-proxy-linux-amd64 /tmp/iptv-proxy-linux-amd64
COPY iptv-proxy-linux-arm64 /tmp/iptv-proxy-linux-arm64
COPY iptv-proxy-linux-armv7 /tmp/iptv-proxy-linux-armv7

RUN set -eux; \
    case "${TARGETARCH}/${TARGETVARIANT}" in \
      amd64/) asset=amd64; expected=ff34976227157319a251770e14b2f907e6237f0001f9d8c5ea79a517a43c01a7 ;; \
      arm64/) asset=arm64; expected=2948ee1f0eff22a48a351653f2df9f29dc424708bacd670f34378476efab5a4b ;; \
      arm/v7) asset=armv7; expected=739516d7705d3134998a9a47ed141d68c1fa8b98ae39df6aa3f6211984af5149 ;; \
      *) echo "Unsupported platform: ${TARGETARCH}/${TARGETVARIANT}" >&2; exit 1 ;; \
    esac; \
    printf '%s  %s\n' "$expected" "/tmp/iptv-proxy-linux-$asset" | sha256sum -c -; \
    install -m 0755 "/tmp/iptv-proxy-linux-$asset" /iptv-proxy

FROM alpine:3.21

ARG INSTALL_FFMPEG=false

RUN set -eux; \
    apk add --no-cache ca-certificates coreutils tzdata wget; \
    if [ "$INSTALL_FFMPEG" = "true" ]; then apk add --no-cache ffmpeg; fi

COPY --from=binary /iptv-proxy /usr/local/bin/iptv-proxy
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-healthcheck.sh

WORKDIR /data
VOLUME ["/data"]
EXPOSE 19899

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/docker-healthcheck.sh"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
