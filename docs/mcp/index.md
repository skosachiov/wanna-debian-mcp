# wanna-debian MCP server

A local, **no-authentication** [Model Context Protocol](https://modelcontextprotocol.io)
server that exposes the `distrotracker` and `pre-dose` analysis logic as MCP
tools. It speaks HTTP (streamable HTTP) and binds to loopback by default.

The server is a thin layer over the existing packages: `distrotracker` for
repository metadata and `predose` for source/binary and dependency analysis.

## Install

The server needs the optional `mcp` dependencies. FastMCP requires Python
>= 3.10, while the core library still supports Python >= 3.8, so the server
is an extra:

```
pip install --user --break-system-packages 'wanna-debian[mcp]'
```

This installs the `wanna-debian-mcp` console script.

## Run the server

```
wanna-debian-mcp --metadata-dir ./metadata
```

Defaults:

- `--host 127.0.0.1` (loopback only)
- `--port 8000`
- `--transport http`
- `--metadata-dir` falls back to `$WANNA_DEBIAN_METADATA_DIR`, then `./metadata`

The MCP endpoint is served at `http://<host>:<port>/mcp`. In container images
the server is started with `--host 0.0.0.0` so the port can be published.

Environment variables: `WANNA_DEBIAN_MCP_HOST`, `WANNA_DEBIAN_MCP_PORT`,
`WANNA_DEBIAN_MCP_TRANSPORT`, `WANNA_DEBIAN_METADATA_DIR`.

The `metadata_dir` argument on the metadata tools overrides the server default
for a single call.

## distro-metadata tools

### `list_distributions`

List the distributions published at a Debian repository base URL.

- `base_url` (required) - repository base URL, e.g. `http://deb.debian.org/debian/`
- `no_check_certificate` - disable TLS verification (default `false`)

### `update_metadata`

Download and store Debian metadata for a base URL into the metadata workspace.

- `base_url` (required)
- `metadata_dir` - override the workspace directory
- `dist` - limit distributions, e.g. `["trixie"]` (default: all)
- `comp` - limit components, e.g. `["main"]`
- `build` - limit build types, e.g. `["binary-amd64", "source"]`
- `sysarch` - system architecture used by distrotracker (default `amd64`)
- `no_check_certificate`
- `force` - refresh even if the local copy looks current (default `false`)

### `search_packages`

Find package records matching requirement expressions. Each requirement may be
`name`, `name=version`, or `name (op version)`.

- `requirements` (required) - list of requirement strings
- `metadata_dir` - workspace to read (default: server workspace)
- `dist`, `comp`, `build`, `arch` - filters
- `by_source` - match source package names instead of binary names
- `latest` / `earliest` - return only the newest / oldest matching version
- `briefly` - return the reduced record field set
- `grep` - regular expression applied to each record

Example: find the newest `bash` in the local trixie metadata:

```
search_packages(requirements=["bash"], dist=["trixie"], latest=True)
```

## dependency-analysis tools

These tools take a path to a parsed metadata file: a `Packages` file (binary
metadata) or a `Sources` file (source metadata), e.g. a file produced by
`update_metadata` or the fixtures under `tests/predose/data/`.

### `resolve_source`

Resolve binary package name(s) to their source package.

- `metadata_file` (required)
- `packages` (required) - binary names, optionally `name=version`
- `add_version` - include the version in the result

### `resolve_binaries`

Resolve source package name(s) to the binary packages they build (search
binary by source name).

- `metadata_file` (required)
- `sources` (required) - source names, optionally `name=version`
- `add_version`
- `latest` - only consider the latest source versions

### `resolve_group`

Resolve the sibling binary packages built from the same source.

- `metadata_file` (required)
- `packages` (required)
- `add_version`
- `latest`

### `dependencies`

Return the transitive dependency set of a package up to `depth`, excluding the
queried package itself.

- `metadata_file` (required)
- `package` (required)
- `depth` - number of dependency hops (default `1`)
- `latest`

### `reverse_dependencies`

Return the packages that directly depend on `package`.

- `metadata_file` (required)
- `package` (required)
- `latest`

### `toposort`

Return a dependency-respecting ordering of the given packages.

- `metadata_file` (required)
- `packages` (required) - packages to order
- `latest`

Example: use a `Sources` file to get a build order:

```
toposort(metadata_file="tests/mcp/data/small_Sources",
         packages=["app", "liba", "libb"])
# => order: libb (level 0), liba (level 1), app (level 2)
```

## Container

Build and run the image (see `Dockerfile` in the repository root):

```
docker build -t wanna-debian-mcp .
docker run --rm -p 8000:8000 -v "$PWD/metadata:/data/metadata" wanna-debian-mcp
```

The image is based on Debian, uses the system `python3` (so the `apt_pkg`
extension from `python3-apt` is importable), installs the `mcp` extra, sets
`WANNA_DEBIAN_METADATA_DIR=/data/metadata`, binds `0.0.0.0`, and exposes port
`8000`.

> **Warning:** the server has no authentication. Binding `0.0.0.0` (as the
> container does) exposes it to any host that can reach the published port.
> Only publish the port on trusted networks and keep the default loopback
> binding when running directly on a workstation.
