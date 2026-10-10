ARG BASE_IMAGE=debian:13
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    WANNA_DEBIAN_METADATA_DIR=/data/metadata \
    WANNA_DEBIAN_MCP_HOST=0.0.0.0 \
    WANNA_DEBIAN_MCP_PORT=8000

# System Python + the APT bindings that distrotracker/predose rely on.
# dctrl-tools and jq are used by some distrotracker code paths.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-apt \
        python3-requests \
        python3-certifi \
        python3-debian \
        dctrl-tools \
        jq \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the project together with the optional MCP (FastMCP) dependencies
# into the system interpreter, so `apt_pkg` from python3-apt stays importable.
COPY pyproject.toml README.md ./
COPY wanna_debian_mcp ./wanna_debian_mcp
COPY distrotracker ./distrotracker
COPY predose ./predose
COPY toposort ./toposort
COPY simplebuilder ./simplebuilder
RUN pip install --break-system-packages --no-cache-dir '.[mcp]'

RUN mkdir -p /data/metadata

EXPOSE 8000

CMD ["wanna-debian-mcp", "--host", "0.0.0.0", "--port", "8000", "--metadata-dir", "/data/metadata"]
