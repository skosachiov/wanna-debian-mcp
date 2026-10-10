# Spec Delta

## Purpose

Tracks Debian distribution package metadata and answers package/source queries
against it, so clients can discover which versions of a package satisfy a set of
version constraints across distributions, components, and architectures.

## ADDED Requirements

### Requirement: Metadata update and tracking
The server SHALL be able to fetch and store package metadata from a Debian repository base URL for the requested distributions, components, and build types, and SHALL reuse the stored metadata for subsequent searches.

#### Scenario: Update then search
- **WHEN** a client requests a metadata update for a base URL and then searches for a package
- **THEN** the search returns records derived from the metadata fetched during that update

#### Scenario: Reuse without re-downloading
- **WHEN** a client searches using previously stored metadata without requesting an update
- **THEN** the server answers from the stored metadata without contacting the remote repository

### Requirement: List tracked distributions
The server SHALL return the list of distributions available at the configured repository.

#### Scenario: Enumerate distributions
- **WHEN** a client requests the distribution list for a repository base URL
- **THEN** the server returns the distribution names found at that repository

### Requirement: Version-constraint package search
Given one or more requirement expressions of the form `name (operator version)`, the server SHALL return the package records whose version satisfies the operator, using Debian version ordering semantics.

#### Scenario: Satisfied constraint
- **WHEN** a client searches for `libpython3.13 (>= 3.13.0~rc3)` and matching records exist
- **THEN** the response contains the records whose version satisfies the comparison

#### Scenario: No matching version
- **WHEN** a client searches for a constraint that no stored package version satisfies
- **THEN** the server reports that no version met the condition without returning unrelated records

#### Scenario: Unknown package
- **WHEN** a client searches for a package that is absent from the stored metadata
- **THEN** the server reports that the package was not found

### Requirement: Search result selection and filtering
The server SHALL let clients restrict results by distribution, component, build type, and architecture, and SHALL let clients select only the latest or only the earliest satisfying version.

#### Scenario: Filter by attributes
- **WHEN** a client provides a distribution, component, build, or architecture filter
- **THEN** only records matching every provided filter are returned

#### Scenario: Latest or earliest selection
- **WHEN** a client requests latest (or earliest) selection
- **THEN** the response contains only the newest (or oldest) version satisfying the constraints

### Requirement: Search by source name
The server SHALL support searching by the source package name instead of the binary package name.

#### Scenario: Source-oriented search
- **WHEN** a client requests a source-oriented search
- **THEN** results are matched and returned using source package and source version fields
