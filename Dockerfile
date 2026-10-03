FROM ghcr.io/prefix-dev/pixi:0.68.1

LABEL org.opencontainers.image.source="https://github.com/annefou/beni-canopy-height-ebv"
LABEL org.opencontainers.image.description="Replication study container for beni-canopy-height-ebv"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# git is needed to install healpix-connector from its pinned commit (pixi.toml).
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the pinned environment first (separate from source copy so the lock
# layer is cached across source-only edits).
COPY pixi.toml pixi.lock /app/
RUN pixi install --locked

COPY . /app

# Mount any required credentials at runtime, e.g.:
#   docker run -v ~/.cdsapirc:/home/mambauser/.cdsapirc beni-canopy-height-ebv
# See data/README.md for per-dataset credential setup.

CMD ["pixi", "run", "snakemake", "--cores", "1"]
