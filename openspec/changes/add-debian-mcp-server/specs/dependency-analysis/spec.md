# Spec Delta

## Purpose

Analyzes parsed Debian `Packages` and `Sources` metadata to resolve
source/binary relationships, compute dependency relationships, and order a
package set for backporting.

## ADDED Requirements

### Requirement: Load Debian metadata files
The server SHALL load a Debian `Packages` or `Sources` file and expose its package records for querying.

#### Scenario: Load valid metadata
- **WHEN** a client provides the path to a valid `Packages` or `Sources` file
- **THEN** subsequent queries operate on the records parsed from that file

#### Scenario: Missing metadata file
- **WHEN** a client provides a path that does not exist
- **THEN** the server reports the failure to load the file without crashing

### Requirement: Resolve binary package to source package
Given a binary package name, the server SHALL return the source package name it was built from.

#### Scenario: Known binary package
- **WHEN** a client resolves a binary package that is present in the metadata
- **THEN** the response contains its source package name

#### Scenario: Unknown binary package
- **WHEN** a client resolves a binary package that is absent from the metadata
- **THEN** the server reports that the package could not be resolved

### Requirement: Resolve source package to binary packages
Given a source package name, the server SHALL return the binary packages produced by that source.

#### Scenario: Source with binary packages
- **WHEN** a client resolves a source package that has binary packages recorded
- **THEN** the response lists the binary package names built from that source

#### Scenario: Unknown source
- **WHEN** a client resolves a source package that is absent from the metadata
- **THEN** the server reports that no binary packages were found

### Requirement: Resolve build group
Given any binary package that belongs to a source build group, the server SHALL return all sibling binary packages built from the same source.

#### Scenario: Member of a build group
- **WHEN** a client resolves the build group for a package built from a source with multiple binaries
- **THEN** the response lists all binary packages of that source

### Requirement: Forward dependency resolution
Given a package and a depth, the server SHALL return the transitive set of package names reachable through dependency relationships up to that depth.

#### Scenario: Multi-level dependencies
- **WHEN** a client requests dependencies of a package with a depth greater than one
- **THEN** the response includes direct and transitively reachable dependency names

#### Scenario: Depth of one
- **WHEN** a client requests dependencies with depth one
- **THEN** the response includes only the direct dependencies

### Requirement: Reverse dependency lookup
Given a package name, the server SHALL return the packages that directly depend on it.

#### Scenario: Package with dependents
- **WHEN** a client requests reverse dependencies for a package that others depend on
- **THEN** the response lists those dependent packages

#### Scenario: Package without dependents
- **WHEN** a client requests reverse dependencies for a package that nothing depends on
- **THEN** the response is empty

### Requirement: Topological sort of a package set
Given a set of package names, the server SHALL return a deterministic ordering that respects their dependency relationships.

#### Scenario: Ordering respects dependencies
- **WHEN** a client requests a topological sort for a set of packages with dependency edges
- **THEN** every package appears after the packages it depends on in the returned ordering

#### Scenario: Repeated request is stable
- **WHEN** the same package set is sorted more than once
- **THEN** the returned ordering is identical each time

### Requirement: Latest-version selection
The server SHALL be able to restrict metadata to the latest version of each package before performing a query.

#### Scenario: Keep only latest versions
- **WHEN** a client requests latest-version selection and a package has several stored versions
- **THEN** queries consider only the newest version of each package
