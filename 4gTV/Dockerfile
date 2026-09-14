FROM alpine:3.21 AS binary

ARG TARGETARCH
COPY 4gtv-linux-amd64 /tmp/4gtv-linux-amd64
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) ;; \
      *) printf 'Unsupported platform: %s (this private build is amd64 only)\n' "$TARGETARCH" >&2; exit 1 ;; \
    esac; \
    printf '%s  %s\n' 'a46ccfa3bd08cd06b3f41f411a1545981824aa405f69dff84fde8d7ac77a597e' '/tmp/4gtv-linux-amd64' | sha256sum -c -; \
    install -m 0555 /tmp/4gtv-linux-amd64 /4gtv

FROM alpine:3.21

RUN apk add --no-cache ca-certificates tzdata \
    && addgroup -S -g 1001 fourgtv \
    && adduser -S -D -H -u 1001 -G fourgtv fourgtv \
    && mkdir -p /data \
    && chown 1001:1001 /data \
    && chmod 0700 /data

COPY --from=binary /4gtv /usr/local/bin/4gtv
COPY --chmod=0555 docker-entrypoint.sh docker-healthcheck.sh /usr/local/bin/
COPY --chmod=0444 docker-common.sh /usr/local/bin/docker-common.sh

ENV PORT=8080 TZ=Asia/Taipei
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8080
USER 1001:1001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/docker-healthcheck.sh"]

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
