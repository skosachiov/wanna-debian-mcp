# Spec Delta

## Purpose

Provides a local, no-authentication MCP server over streamable HTTP that
exposes the `wanna-debian` analysis and build helper functions as discoverable
tools for MCP clients, and can be run directly or from a container.

## ADDED Requirements

### Requirement: HTTP MCP transport without authentication
The server SHALL expose the Model Context Protocol over streamable HTTP and SHALL NOT require client authentication or credentials.

#### Scenario: Client connects without credentials
- **WHEN** an MCP client connects to the server's HTTP endpoint without any authentication header or token
- **THEN** the connection succeeds and the client can initialize a session and invoke tools

#### Scenario: Unsupported protocol request is rejected
- **WHEN** a client sends a request using an unsupported transport or protocol version
- **THEN** the server responds with a protocol error and does not terminate

### Requirement: Configurable bind address
The server SHALL allow its listening host and port to be configured, and SHALL default to binding on the loopback interface.

#### Scenario: Default binding
- **WHEN** the server is started with no host or port configured
- **THEN** it listens on the loopback interface on the default port

#### Scenario: Custom binding
- **WHEN** the server is started with a configured host and port
- **THEN** it listens for HTTP connections on that host and port

### Requirement: Tool discovery
The server SHALL register every supported `wanna-debian` operation as an MCP tool with a stable name and a human-readable description, and SHALL return them from a tool-listing request.

#### Scenario: List available tools
- **WHEN** an initialized client requests the list of tools
- **THEN** the response includes the distrotracker and pre-dose tools with their names, descriptions, and input schemas

### Requirement: Structured tool results and errors
Each tool SHALL return a structured result on success and a structured, non-fatal error on invalid input or an unsatisfiable request, without ending the server process.

#### Scenario: Successful tool call
- **WHEN** a client calls a tool with valid arguments
- **THEN** the server returns the operation's structured result

#### Scenario: Invalid arguments
- **WHEN** a client calls a tool with missing or malformed arguments
- **THEN** the server returns an error result describing the problem and remains available for further calls

#### Scenario: Operation failure is isolated
- **WHEN** a tool call fails while processing (for example, a referenced metadata file is missing)
- **THEN** the server reports the failure in that tool's result and continues serving other requests

### Requirement: Container packaging
The repository SHALL provide a Dockerfile that builds an image able to run the HTTP MCP server without manual installation steps.

#### Scenario: Build and run the image
- **WHEN** the image is built from the provided Dockerfile and a container is started from it
- **THEN** the container runs the HTTP MCP server and serves tool requests on its exposed port without requiring authentication
