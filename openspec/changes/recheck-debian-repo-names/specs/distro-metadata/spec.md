# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
