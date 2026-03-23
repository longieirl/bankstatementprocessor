# check=skip=SecretsUsedInArgOrEnv
# Multi-stage Docker build for bankstatements-free
# Stage 1: Builder - installs dependencies
# Stage 2: Production - minimal runtime image

FROM python:3.12-slim AS base

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# ============================================================================
# STAGE 1: Builder
# ============================================================================
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip wheel setuptools build

COPY packages/parser-core/ ./packages/parser-core/
COPY packages/parser-free/ ./packages/parser-free/

RUN pip install --no-cache-dir ./packages/parser-core
RUN pip install --no-cache-dir ./packages/parser-free

# Expose site-packages via a stable path so the production COPY is version-agnostic
RUN ln -s "$(python -c 'import sysconfig; print(sysconfig.get_path(\"purelib\"))')" /pkg

# ============================================================================
# STAGE 2: Production
# ============================================================================
FROM base AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

WORKDIR /app

# Copy installed packages using the version-agnostic symlink created in builder.
# Both stages share the same base image so the Python version always matches.
# We use --mount=type=bind to read from the builder's resolved symlink path,
# then cp into the correct versioned site-packages directory.
RUN --mount=type=bind,from=builder,source=/pkg,target=/mnt/pkg \
    dest="$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" && \
    mkdir -p "$dest" && \
    cp -a /mnt/pkg/. "$dest/"
COPY --from=builder /usr/local/bin/bankstatements /usr/local/bin/bankstatements

COPY entrypoint.sh .

RUN chmod +x entrypoint.sh && \
    mkdir -p /app/input /app/output /app/logs && \
    chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1
ENV DO_NOT_TRACK=1
ENV TELEMETRY_DISABLED=true
ENV ANALYTICS_DISABLED=true
ENV NO_ANALYTICS=1
ENV SENTRY_DSN=""
ENV SEGMENT_WRITE_KEY=""

LABEL org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="bankstatements-free" \
      org.opencontainers.image.description="Bank Statement PDF Processor (Free)" \
      org.opencontainers.image.source="https://github.com/longieirl/bankstatementprocessor"

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import bankstatements_free; import bankstatements_core" || exit 1

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
