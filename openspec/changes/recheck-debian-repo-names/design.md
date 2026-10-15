# Design

## Context

See `proposal.md - Why`. Current state that shapes the approach:

- `wanna_debian_mcp/tools.py` wraps `distrotracker`.
  `distrotracker.distrotracker.config` is a module-level dict that acts as a
  process-wide contract; `update_metadata()` reads it for `local_dir`,
  `config_file`, `sysarch`, `timestamp` and `consistency`, and writes
  `config.json` mid-call.
- `_pull_into_workspace()` mutates that global in place and only overwrites the
  fields the caller passed (`if dist:`, `if comp:`, `if build:`). Fields left
  out keep their previous process-wide values, which are then dumped into the
  new workspace's `config.json`.
- Each workspace directory corresponds to exactly one base URL
  (`local_dir is a dir for base-url`). On disk a workspace holds
  `<metadata root>/<workspace>/dists/<dist>/<component>/<build>/`.
- `distrotracker`'s module defaults are the repository-independent baseline:
  `dist = []` (all), `comp = ['main', 'main/debian-installer', 'contrib',
  'non-free', 'non-free-firmware']`, `builds = ['binary-amd64', 'source']`,
  `sysarch = "amd64"`.

## Goals / Non-Goals

**Goals:**

- A workspace's persisted `dist` / `comp` / `builds` / `sysarch` derive only
  from that workspace's explicit inputs and its own stored config, never from
  another workspace.
- Keep a fresh workspace's defaults unchanged (no repository-specific
  knowledge added).
- Keep the `distrotracker` global contract that drives the pull working.

**Non-Goals:**

- Repository-specific behavior (auto-detecting Ubuntu `universe`/`multiverse`,
  discovering distributions/components from the archive).
- Changing MCP tool signatures, response shapes, `config.json` fields, or the
  on-disk layout.
- Refactoring `distrotracker`'s global into an explicit config object.

## Decisions

### Snapshot the distrotracker defaults once, at import

Capture the repository-independent baseline before any tool call can mutate the
global:

```python
_DEFAULT_DIST = list(_dt.config["dist"])
_DEFAULT_COMP = list(_dt.config["comp"])
_DEFAULT_BUILDS = list(_dt.config["builds"])
_DEFAULT_SYSARCH = _dt.config["sysarch"]
```

Rationale: keeps `distrotracker` as the single source of truth for defaults and
survives the global having been mutated by an earlier call. *Alternative:*
hardcode a repository-neutral component list in the MCP layer — rejected, it
duplicates knowledge and can diverge from `distrotracker`.

### Always assign every filter field in `_pull_into_workspace`

Resolve each field to a concrete value and write all of them to the global
unconditionally, so nothing is left over from a previous workspace:

```python
cfg["base_url"] = base
cfg["ssl_verify"] = not no_check_certificate
cfg["local_dir"] = [resolved_dir]
cfg["sysarch"] = sysarch or _DEFAULT_SYSARCH
cfg["dist"] = list(dist) if dist else list(_DEFAULT_DIST)
cfg["comp"] = list(comp) if comp else list(_DEFAULT_COMP)
cfg["builds"] = list(build) if build else list(_DEFAULT_BUILDS)
```

`update_metadata()` already fills `dist` / `comp` / `builds` / `sysarch` from the
workspace's own stored `config.json` before calling this, so a stored workspace
keeps its own values; a fresh workspace gets the baseline instead of another
workspace's values. The resolved values are what get persisted, so `config.json`
is self-contained.

*Alternatives:* reset only the three filter fields (smaller, but leaves the
assignment mistake easy to reintroduce); build the persisted dict from scratch
(equal behavior, but `distrotracker`'s mid-call write already dumps the global,
so the global must be correct anyway — assigning all fields is the least
invasive fix that covers both writes).

### Keep the existing lock and pull path

`_LOCK` already serializes everything that touches the global. Resolve, assign,
pull and persist stay inside it; the mutation window is unchanged.

## Risks / Trade-offs

- [Behavior change] Workspaces that previously (incorrectly) persisted an
  inherited filter now persist the baseline, so results differ → this is the
  intended fix; note it in the change summary.
- [First-call mutation] If some other code mutated `_dt.config` before the
  snapshot, the baseline constants would be wrong → snapshot at import, before
  any tool call.
- [Existing polluted configs] A workspace whose `config.json` already contains a
  leaked filter stays wrong until it is re-initialized or deleted → document the
  recovery step; no automatic rewrite (a stored value is the workspace's own
  contract).

## Migration Plan

Code-only. Existing workspaces load their stored config and are unaffected on
update; no data migration. Workspaces with an already-polluted config must be
re-initialized. Rollback is reverting the `_pull_into_workspace` change.

## Open Questions

None that affect the specs or approach. Automatic component discovery for
non-Debian repositories is explicitly out of scope.
