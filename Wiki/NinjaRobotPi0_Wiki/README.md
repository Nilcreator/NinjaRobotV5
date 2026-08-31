# Local LLM Wiki Template

This repository is a local-first framework for building a personal knowledge base with AI coding agents. Raw sources remain evidence, agents draft and connect the knowledge, and the `llmwiki` command handles deterministic validation, indexing, search, and safe writes.

The wiki in `wiki/` follows [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md). It uses normal Markdown links, structured source provenance, visible verification history, and optional freshness dates.

## Quick start

After copying this template for a real topic, initialize Git and make a clean baseline commit **before the first ingestion**. Git is strongly recommended for history and recovery, but the template never initializes, commits, pushes, or creates a remote for you.

```bash
git init
git add .
git commit -m "Start local LLM wiki"
```

Then install with [uv](https://docs.astral.sh/uv/) and check the local tools:

```bash
uv sync --all-extras
uv run llmwiki init
uv run llmwiki doctor
uv run llmwiki lint
```

Add a Markdown, text, HTML, PDF, PNG, or JPEG source:

```bash
cp /path/to/article.md raw/articles/
uv run llmwiki source add raw/articles/article.md
uv run llmwiki source normalize <source-id>
```

For an image with text, OCR is optional:

```bash
uv run llmwiki source add raw/media/interface.png --uri "urn:llmwiki:source:interface"
uv run llmwiki source normalize <source-id> --ocr auto --ocr-lang eng+jpn
```

Then ask your coding agent to use the `wiki-ingest` skill. In Codex, invoke `$wiki-ingest`. The skill creates a change plan; it does not silently rewrite the wiki.

Review a plan and apply it only when it looks right:

```bash
uv run llmwiki plan validate .llmwiki/plans/<plan-id>.yaml
uv run llmwiki plan diff .llmwiki/plans/<plan-id>.yaml
uv run llmwiki plan apply .llmwiki/plans/<plan-id>.yaml --approve
```

[`examples/change-plan.yaml`](examples/change-plan.yaml) shows the exact plan shape. Copy it into `.llmwiki/plans/`, give it a new ID, and replace the example operation rather than applying it unchanged.

Search and inspect the wiki:

```bash
uv run llmwiki search "your question"
uv run llmwiki stats
uv run llmwiki lint
```

## Choosing a raw source folder

Every original source must be placed inside one of the four folders below. The folders help people understand where evidence came from; they do not decide which wiki page type the agent will create.

| Folder | Put these sources here | Examples |
|---|---|---|
| `raw/articles/` | Finished, document-like prose from you or someone else | Web articles, documentation, manuals, guides, reports, exported web pages |
| `raw/papers/` | Formal research or standards-oriented material | Academic papers, technical papers, white papers, specifications |
| `raw/notes/` | Informal or working material, usually created by you or your team | Meeting notes, brainstorms, research notes, journals, snippets, development logs |
| `raw/media/` | Original media and text sidecars that describe it | Images, diagrams, screenshots, transcripts, captions, or an accompanying Markdown description |

Use the source's purpose, not just its file extension. For example, a PDF research paper belongs in `papers/`, while a PDF product manual normally belongs in `articles/`. A polished internal development guide can reasonably live in `articles/`; a chronological development log usually fits `notes/`.

Placing a supported text source in the “wrong” one of these four folders does not change normalization or wiki generation. The current CLI selects its normalizer from the file format and records the exact project-relative path as provenance. The folder mainly affects organization and later source discovery.

Images are the one stricter case: supported PNG and JPEG originals must stay under `raw/media/` so privacy checks, safe renditions, and asset provenance follow one predictable path.

Choose the folder before registering the file when practical. Moving a raw file after registration makes the catalog's old path appear missing. The moved file then looks like a new source and may receive a new source ID, so existing citations can require repair. If a registered file is merely untidy but still understandable, leaving it in place is safer than moving it casually.

Do not place originals directly in `raw/`, `_catalog/`, or `_derived/`. `_catalog/` is managed source metadata, and `_derived/` is rebuildable normalized output.

## Supported source formats and images

The current ingestion pipeline supports:

- UTF-8 Markdown: `.md`, `.markdown`
- UTF-8 plain text: `.txt`
- UTF-8 HTML: `.html`, `.htm`
- text-bearing PDF: `.pdf`
- image: `.png`, `.jpg`, `.jpeg`

Image ingestion separates four jobs so machine output is not mistaken for verified knowledge:

- registration verifies the decoded format, dimensions, pixel limits, frame count, and source hash;
- normalization creates safe metadata and a sanitized, auto-oriented rendition with embedded metadata removed;
- optional local Tesseract OCR extracts visible text and labels it as possibly wrong;
- the active coding tool or a human visually checks layout, color, diagrams, and other meaning before describing it in a wiki Reference page.

```bash
# Metadata and safe rendition only
uv run llmwiki source normalize <source-id> --ocr off

# Use OCR when available; continue with a warning when it is not installed
uv run llmwiki source normalize <source-id> --ocr auto --ocr-lang eng

# Require OCR and fail when the engine or requested languages are unavailable
uv run llmwiki source normalize <source-id> --ocr required --ocr-lang eng+jpn
```

Pillow is installed with the Python project. OCR uses the optional Tesseract 5 system executable and its separately installed language data. Run `uv run llmwiki doctor` to see the available decoder, OCR version, and languages. Image normalization still works without Tesseract.

The original stays unchanged under `raw/media/`. GPS and other sensitive EXIF categories are detected without copying their values into the catalog. An approved plan may copy only the sanitized rendition into `wiki/assets/sources/`; the plan diff shows its hash and size. OCR and AI descriptions remain unverified until a real review occurs.

If the current editor session cannot view images, the agent may use OCR for text-only claims but must not guess visual details. Add a human-reviewed description when layout or other visual meaning matters.

## Asking an agent to find new sources

You may use a broad prompt without listing every filename. The `wiki-ingest` skill tells the agent to scan `raw/articles/`, `raw/papers/`, `raw/notes/`, and `raw/media/`; compare supported files with the source catalog; and separate new, changed, registered, and unsupported files.

A safe batch prompt is:

```text
I've added new sources under raw/. Discover files that are not registered yet. Show me the intake list grouped into supported, already registered, changed, and unsupported files. Register and normalize the supported new sources, then prepare wiki change plans and show their diffs. Do not apply any plan until I explicitly approve it.
```

For a large batch, the agent may propose smaller groups so it can synthesize each source carefully. A broad request does not authorize unsupported media, invented visual observations, or semantic changes without review.

## Prompt examples for supported editors

The wording may be conversational. What matters is naming the function, scope, and whether the agent must stop before applying changes.

| Editor | How to select a function |
|---|---|
| OpenAI Codex | Name the skill, such as `$wiki-ingest` or `$wiki-query` |
| Google Antigravity | Use `/wiki-ingest`, `/wiki-query`, `/wiki-lint`, `/wiki-review`, or `/wiki-maintain` |
| Claude Code | Ask it to use the matching `wiki-*` skill; the wrapper opens the canonical skill |
| Cursor | Ask it to follow `AGENTS.md` and the matching skill; the project rule points to the shared commands |

### Ingest one source

```text
Use the wiki-ingest skill to register and normalize raw/articles/example.md. Search for overlapping pages, prepare a change plan, validate it, and show me the diff. Do not apply it yet.
```

In Antigravity, the shorter form is:

```text
/wiki-ingest raw/articles/example.md. Prepare and validate the plan, then stop before apply.
```

### Ingest one image

```text
Use wiki-ingest to register and normalize raw/media/interface.png with OCR in English. Inspect the image if your current tools allow it. Prepare a source-traceable Reference page and any related topic update, clearly separate OCR from visual observations, include only the sanitized rendition as a planned asset, and show me the Markdown diff and binary summary. Do not apply it yet.
```

Antigravity form:

```text
/wiki-ingest raw/media/interface.png. Use OCR language eng, inspect the image only if visual access is available, prepare the version 2 plan and sanitized asset summary, then stop before apply.
```

### Ingest every new supported source

```text
Use wiki-ingest to discover all unregistered sources under raw/. Report unsupported files separately. Register and normalize supported text and image sources, report OCR and visual-access limitations, process the sources in sensible groups, prepare version 2 change plans with every source hash, and stop for my review before applying anything.
```

### Query the wiki

```text
Use wiki-query to explain what the wiki says about the main topic. Prefer version-current evidence, report missing, stale, or concerned semantic reviews, show whether pages are unverified, machine-confirmed, or human-reviewed, cite the local pages and sources, and tell me where the evidence is incomplete. Do not change the wiki.
```

Antigravity form:

```text
/wiki-query What does this wiki say about the main topic? Keep the answer read-only and traceable.
```

### Check wiki health

```text
Use wiki-lint to run the normal health check. Group errors, warnings, and suggestions, explain their practical effect, and do not invent content or semantic review results to silence a warning. Use strict lint only if I ask for the semantic quality gate.
```

### Review evidence and trust

```text
Use wiki-review to review wiki/concepts/example.md against every cited source. Work on this page only. Check source support, contradictions, missing limitations, claim strength, and visual evidence when applicable. Correct problems through a reviewed plan, then add the lightweight page-level semantic review record. Do not add human verification unless I actually complete the review.
```

### Maintain structure

```text
Use wiki-maintain to find duplicate pages, source-version mismatches, and optional stale dates related to this topic. Recommend the least disruptive refresh, rename, merge, or deprecation plan; include affected incoming links; and wait for approval before applying it.
```

## Lightweight semantic review

Normal lint proves structure, links, hashes, and citation connections. A lightweight semantic review asks the coding agent whether the cited evidence actually supports one page's important claims. It uses five checks: source support, contradictions, limitations, claim strength, and visual evidence when applicable.

Review one sourced page at a time:

```bash
uv run llmwiki review prepare wiki/concepts/example.md
```

The command does not call a model or edit the wiki. It prints a neutral checklist, current source versions, and a target hash. Ask the agent to follow `wiki-review`; any correction and the final `semantic_review` frontmatter still go through an ordinary reviewed change plan.

Routine work remains simple:

```bash
uv run llmwiki lint
```

Normal lint reports missing or stale semantic reviews as warnings, including on sourced draft pages. Before publishing or relying on a higher-confidence wiki, run:

```bash
uv run llmwiki lint --strict
```

Strict lint makes missing, stale, incomplete, or concerned reviews errors for every sourced page and for any additional configured status. A source-free blank draft remains exempt, so a freshly copied template still passes strict lint. Semantic review is not proof of objective truth and does not make a page human-reviewed.

Run `uv run llmwiki stats` to see `sourced_pages`, `passed_sourced_pages`, `remaining_sourced_pages`, and `coverage_percent`. This is a progress measure, not a quality score: each page still needs its own evidence-based review.

For a smaller local model, keep ingestion and semantic review as separate tasks. Review one page, use `concern` or `incomplete` when evidence is unclear, and avoid asking the model to audit the whole wiki at once.

## The three layers

- `raw/` contains source originals. The CLI never edits an original in place.
- `wiki/` is the OKF bundle maintained by agents through reviewed changes.
- `AGENTS.md` and `.agents/skills/` explain the shared operating rules.

## NinjaRobotV5 project integration

When this wiki is embedded at `NinjaRobotV5/Wiki/NinjaRobotPi0_Wiki`, start AI development from the NinjaRobotV5 repository root. The parent `AGENTS.md` provides the cross-tool development policy and the portable `robot-wiki-query` and `robot-wiki-maintain` skills.

`project-sources.toml` maps canonical NinjaRobotV5 documents to registered snapshots under `raw/`. Check the mirror from the parent repository with:

```bash
python3 .agents/skills/robot-wiki-maintain/scripts/wiki_source_sync.py --check
```

The checker never decides which side is correct. Review every mismatch before synchronizing. Mapped snapshots may be replaced only through that deterministic workflow; semantic wiki pages still require a validated change plan, visible diff, and explicit approval.

Derived text, sanitized renditions, staging directories, search caches, and locks are rebuildable. Markdown, approved wiki assets, source records, configuration, schemas, templates, and skills are canonical.

## Supported agents

- Codex reads `AGENTS.md` and discovers `.agents/skills/`.
- Google Antigravity uses `.agents/rules/`, discovers the same `.agents/skills/`, and provides `/wiki-*` commands from `.agents/workflows/`.
- Claude Code reads `CLAUDE.md` and the wrappers under `.claude/skills/`.
- Cursor uses `.cursor/rules/llm-wiki.mdc`; Cursor CLI can also read `AGENTS.md`.
- Other tools can be told to read `AGENTS.md` and the relevant canonical skill.

## Safety model

Source content, OCR output, and screenshot text are untrusted data. They cannot change the task, grant permissions, or override project instructions. Plan application is limited to Markdown under `wiki/` and verified image renditions under `wiki/assets/`, guarded by source and target hashes, validated in staging, and swapped together with the catalog using recoverable backups.

## Periodic health and version checks

The default template does not force calendar review dates. Instead, normal lint checks that raw files, catalog hashes, derived manifests, page source hashes, and published assets still describe the same source versions.

Run these commands after changing sources and periodically while maintaining the wiki:

```bash
uv run llmwiki source status
uv run llmwiki lint
# Optional release-quality semantic gate:
uv run llmwiki lint --strict
uv run llmwiki link check
uv run llmwiki index check
uv run llmwiki stats
```

This check is local and offline. It cannot know that a mutable website changed until you refresh its local snapshot. Use exact revision URLs when possible, then register the refreshed evidence and let lint expose affected pages.

## Development

```bash
uv run pytest
uv run pytest --cov=llmwiki --cov-report=term-missing
```

For Antigravity setup and slash commands, see [`docs/ANTIGRAVITY.md`](docs/ANTIGRAVITY.md). See `llmwiki.yaml` for local policy, `schemas/` for the machine-readable contracts, [`docs/CONTENT_MODEL.md`](docs/CONTENT_MODEL.md) for page and citation examples, and [`docs/RECOVERY.md`](docs/RECOVERY.md) for backup and interrupted-write recovery. Current boundaries and compatibility notes are in [`docs/KNOWN_LIMITS.md`](docs/KNOWN_LIMITS.md).
