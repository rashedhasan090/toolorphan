# toolorphan

**Offline CLI that diffs an agent tool manifest against tool-call JSONL — finds orphaned and rogue tools.**

Agent stacks accumulate tool surface over time: manifests list tools that nobody calls anymore, and logs show calls to tools that were never declared. `toolorphan` reports both sides so you can shrink allowlists, retire dead tools, and catch undeclared surface before it becomes policy debt.

## Why this is novel

Prompt linters (promptfence) score instructions. Callstorm finds retry storms in JSONL. Toolflow draws Mermaid diagrams of call sequences. Stubtruth checks README claims against code. **toolorphan** is different: it treats the **declared tool set as a contract against observed invocations**, and fails CI when orphans or rogues appear.

It is **not** a fork or thin wrapper of an existing project.

Distinct from: sandclock, tokpack, hushdiff, runseal, toolflow, hedgescope, diffintent, promptfence, aegispath, rippleguard, shardroom, claimcite, citationcheckertool, stubtruth, callstorm.

## Install

```bash
pip install -e .
# or
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Usage

```bash
# Diff a manifest against one or more JSONL logs
toolorphan -m examples/manifest.json -l examples/run.jsonl

# Multiple logs
toolorphan -m examples/manifest.yaml -l run1.jsonl -l run2.jsonl

# JSON for tooling
toolorphan -m examples/manifest.json -l examples/run.jsonl --format json

# CI gates
toolorphan -m manifest.json -l agent.jsonl --fail-on-orphan --fail-on-rogue
toolorphan -m manifest.json -l agent.jsonl --max-orphan-ratio 0.2 --min-coverage 0.8
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK (or no failing gates requested) |
| 1 | Bad args / missing files / parse error |
| 2 | `--fail-on-orphan` and at least one orphan |
| 3 | `--fail-on-rogue` and at least one rogue |
| 4 | `--max-orphan-ratio` exceeded |
| 5 | `--min-coverage` not met |

## Demo

The bundled examples declare five tools; the sample log calls three of them plus two undeclared ones:

```bash
toolorphan -m examples/manifest.json -l examples/run.jsonl --fail-on-orphan --fail-on-rogue
# orphans: SendEmail, LegacyDB
# rogues: UndeclaredHack, GhostMCP
# exit 2
```

## How it works

1. Load declared names from a JSON or YAML-ish manifest (OpenAI-style `tools[]`, keyed maps, bare name lists).
2. Scan tool-call JSONL for `tool` / `name` / `function.name` / `tool_calls[]` fields (skips pure results without a tool name).
3. Diff: **matched**, **orphans** (declared ∩ never called), **rogues** (called ∉ declared).
4. Report text or JSON; optionally gate with CI exit codes.

## Manifest shapes supported

```json
{ "tools": [ {"name": "Shell"}, {"name": "Read"} ] }
```

```json
{ "tools": { "Shell": {}, "Read": {} } }
```

```yaml
tools:
  - name: Shell
  - name: Read
```

## Limitations

- Offline only — does not talk to live agent runtimes.
- YAML support is a lightweight subset (no full PyYAML); prefer JSON for complex manifests.
- Tool rename aliases are not inferred; `Shell` and `shell` are different names.
- Defensive analysis only: no exploit generation, no credential access.

## License

MIT
