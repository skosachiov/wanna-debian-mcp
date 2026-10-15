# distro-metadata Specification

## Purpose

Initializes and refreshes named Debian metadata workspaces under the server's
metadata root, persisting each workspace's repository configuration so later
updates reuse it instead of requiring the client to resend the base URL.

## Requirements

### Requirement: Named metadata workspace initialization

The system SHALL initialize a named metadata workspace under the server metadata
root given a repository base URL: it SHALL persist the workspace configuration
(base URL, distributions, components, builds, architecture, TLS setting) and
perform an initial metadata pull, and SHALL report the resolved workspace
directory. Filters omitted by the client SHALL resolve to repository-independent
defaults for the new workspace, not to values persisted by any other workspace.

#### Scenario: Initialize a new workspace

- **WHEN** a client initializes workspace `debian` with base URL `http://ftp.debian.org/debian/`
- **THEN** the server fetches metadata from that URL and persists the workspace configuration in the workspace directory

#### Scenario: Workspace name resolves under the metadata root

- **WHEN** a client names a workspace that is not an absolute path
- **THEN** the workspace directory is `<metadata root>/<name>`

#### Scenario: Missing base URL is rejected

- **WHEN** a client initializes a workspace without a base URL
- **THEN** the request fails with an error and no workspace configuration is written

#### Scenario: Omitted filters use repository-independent defaults

- **WHEN** a client initializes a new workspace without specifying distributions, components, or builds
- **THEN** the persisted configuration records the repository-independent defaults and not values carried over from any other workspace

### Requirement: Update from stored workspace configuration

The system SHALL refresh an initialized workspace using the base URL and filters
persisted in its configuration when the client supplies no base URL of its own.

#### Scenario: Update reuses the stored base URL

- **WHEN** a client updates an initialized workspace without supplying a base URL
- **THEN** the server refreshes metadata from the stored base URL without requiring the client to resend it

#### Scenario: Uninitialized workspace without a base URL fails

- **WHEN** a client updates a workspace that has no stored configuration and supplies no base URL
- **THEN** the server returns an error instructing the client to initialize the workspace first

### Requirement: Explicit base URL handling on update

The system SHALL accept an optional base URL on update; when one is supplied it
SHALL fetch from that URL and persist it to the workspace configuration, and
SHALL reject a URL that conflicts with the workspace's stored base URL.

#### Scenario: Explicit base URL initializes a config-less workspace

- **WHEN** a client updates a workspace that has no stored configuration and supplies a base URL
- **THEN** the server fetches metadata from that URL and persists it for later updates

#### Scenario: Conflicting base URL is rejected

- **WHEN** a client supplies a base URL that differs from the workspace's stored base URL
- **THEN** the server rejects the request and leaves the stored configuration unchanged

### Requirement: Per-workspace configuration isolation

The system SHALL derive and persist the distribution, component, and build
filters of each metadata workspace independently of every other workspace, so
that configuring a repository whose names are not Debian's (for example an
Ubuntu repository) never reuses another workspace's values.

#### Scenario: A new workspace does not inherit an earlier workspace's distributions

- **WHEN** a client initializes workspace `debian` for `http://ftp.debian.org/debian/` with distributions `["trixie"]` and then initializes workspace `ubuntu` for `http://archive.ubuntu.com/ubuntu/` without distributions
- **THEN** the `ubuntu` workspace configuration selects all distributions and does not contain `trixie`

#### Scenario: A new workspace does not inherit an earlier workspace's components

- **WHEN** a client initializes workspace `ubuntu` for `http://archive.ubuntu.com/ubuntu/` without components after another workspace was configured with Debian-specific components
- **THEN** the `ubuntu` workspace configuration records the repository-independent default components, not the earlier workspace's components

#### Scenario: Updating a workspace uses only its own stored configuration

- **WHEN** a client updates workspace `ubuntu` without supplying filters
- **THEN** the server refreshes from the `ubuntu` workspace's own stored base URL and filters, never from another workspace's configuration
