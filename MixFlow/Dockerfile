# syntax=docker/dockerfile:1.7
FROM alpine:3.21 AS binary

ARG TARGETARCH

COPY mixflow-linux-amd64 /tmp/mixflow-linux-amd64
COPY mixflow-linux-arm64 /tmp/mixflow-linux-arm64

RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) asset=amd64; expected=071624c66e9ef2ecb1a46e87d8805f7e2bdac123b179f32e2d9b2d0a16a30853 ;; \
      arm64) asset=arm64; expected=7498561d2737e522802a76e51b748457a57e730e1d62aacfea0cc08bc8f0ef65 ;; \
      *) echo "Unsupported platform: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    printf '%s  %s\n' "$expected" "/tmp/mixflow-linux-$asset" | sha256sum -c -; \
    install -m 0755 "/tmp/mixflow-linux-$asset" /mixflow

FROM alpine:3.21

RUN apk add --no-cache ca-certificates iproute2 iptables tzdata wget

COPY --from=binary /mixflow /usr/local/bin/mixflow
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-healthcheck.sh

WORKDIR /data
VOLUME ["/data"]
EXPOSE 12321

# WARP requires /dev/net/tun and NET_ADMIN at runtime (configured in Compose).
LABEL org.opencontainers.image.title="MixFlow" \
      org.opencontainers.image.description="Multi-protocol proxy and Web panel" \
      org.opencontainers.image.capabilities="NET_ADMIN"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/docker-healthcheck.sh"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
