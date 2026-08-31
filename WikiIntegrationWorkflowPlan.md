# NinjaRobotV5 Wiki Integration Workflow Plan

## Objective

Make `Wiki/NinjaRobotPi0_Wiki` the local, traceable knowledge layer used by Codex, Claude Code, Google Antigravity, and Cursor during NinjaRobotV5 development, without changing robot runtime behavior.

## Findings from the existing workflow

- The wiki already has strong internal controls: immutable raw evidence, source hashes, OKF pages, semantic review records, reviewed change plans, transactional apply, and normal/strict lint modes.
- The wiki is internally healthy, but its adapters are scoped to the nested wiki. An agent launched from the NinjaRobotV5 root does not reliably discover those skills.
- The project uses `AGENT.md`, while Codex and several other tools recognize `AGENTS.md`.
- `GEMINI.md` duplicated older guidance and referenced files/contracts that no longer match the repository.
- The project skills did not query the wiki before development or require a wiki-maintenance gate after documentation changes.
- Project documents are copied into `raw/` as registered evidence, but there was no deterministic mapping or drift check between the canonical project documents and those snapshots.
- The nested wiki contains its own Git repository, which prevents normal inclusion as files in the parent NinjaRobotV5 repository.

## Target architecture

```text
NinjaRobotV5/
├── AGENTS.md                         canonical cross-tool instructions
├── AGENT.md                          legacy pointer
├── CLAUDE.md                         Claude Code adapter
├── GEMINI.md                         Google Antigravity adapter
├── .agents/
│   ├── rules/                        Antigravity always-on rule
│   ├── workflows/                    Antigravity slash workflows
│   └── skills/                       portable canonical skills
├── .claude/skills/                   thin Claude Code wrappers
├── .cursor/rules/                    Cursor always-on rule
└── Wiki/NinjaRobotPi0_Wiki/
    ├── project-sources.toml           project-to-raw source map
    ├── raw/                           registered evidence snapshots
    └── wiki/                          reviewed knowledge pages
```

Codex, Antigravity, and Cursor use `.agents/skills/` directly. Claude Code uses wrappers so the workflow still has one maintained source. Tool adapters contain discovery instructions only; they do not duplicate the development policy.

## Refined development workflow

### 1. Retrieve before deciding

For substantial work or decisions involving architecture, APIs, configuration, hardware, protocols, deployment, or known problems:

1. Run `robot-wiki-query`.
2. Read the strongest matching pages and their source records.
3. Record page status, source-version state, and semantic-review state.
4. Verify implemented behavior against current code and tests.
5. Put conflicts or missing evidence into the implementation plan.

### 2. Implement without expanding authority

1. Preserve existing robot behavior unless the user approves a behavior change.
2. Keep wiki retrieval read-only.
3. Use the existing driver, documentation, and Pi validation skills when they match.
4. Validate locally before proposing any hardware test.

### 3. Maintain after changing knowledge

1. Update and fact-check the canonical project docs.
2. Run the project-source drift checker.
3. Review every mismatch; never overwrite an unexplained conflict.
4. Synchronize intentional project-document changes into their registered raw snapshots.
5. Normalize changed sources and prepare the smallest wiki change plan.
6. Show the plan diff and wait for explicit approval before semantic apply.
7. Review affected sourced pages, run lint, and report any remaining drift or stale review.

### 4. Completion gates

A task that changes documented knowledge is complete only when:

- relevant local tests/lint pass;
- project documentation is updated;
- the source-mirror check is clean or each remaining mismatch is explicitly explained;
- required wiki changes have a validated plan and approval state is reported;
- normal wiki lint has no errors after any approved apply;
- Raspberry Pi validation is reported as executed or pending, never implied.

## Rollout and verification

1. Validate all canonical skills with the Agent Skills validator.
2. Run the source-mirror checker from outside the wiki directory.
3. Run wiki doctor, source status, stats, normal lint, and the wiki test suite.
4. Confirm the parent repository sees the wiki as ordinary files after the nested `.git` directory is removed.
5. Forward-test these scenarios in fresh tool sessions:
   - architecture question uses `robot-wiki-query` and cites local evidence;
   - driver change loads the driver skill and wiki evidence before planning;
   - documentation-only change triggers the mirror checker and maintenance workflow;
   - conflicting wiki/code claim is reported rather than silently copied;
   - hardware commands remain unexecuted until a controlled Pi validation step.

## Non-goals

- No robot runtime, driver, protocol, hardware, configuration, or UI behavior changes.
- No automatic semantic wiki edits without a reviewed `llmwiki` plan.
- No automatic Git commit, push, remote creation, package installation, or hardware actuation.
- No MCP server until local file-based retrieval proves insufficient.
