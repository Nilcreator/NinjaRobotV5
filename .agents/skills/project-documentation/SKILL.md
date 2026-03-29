---
name: project-documentation
description: Use when implementation work changes behavior, setup, drivers, architecture, or developer workflow and the NinjaRobotV5 documentation must be reviewed, fact-checked against the code, and updated before the task is considered complete.
---

# Project Documentation Maintainer

Documentation updates are mandatory when implementation changes behavior or developer workflow.

## Review targets
- README.md
- DevelopmentGuide.md
- DevelopmentLog.md
- InstallationGuide.md when setup, calibration, config import, or hardware bring-up changes
- the affected package `README.md`
- AGENT.md and relevant skill files when the project workflow changes

## Source-of-truth rule

Before editing docs, verify important claims against:

1. current code
2. tests and commands actually run
3. package metadata and entry points
4. existing docs

Do not copy stale claims from one document into another.

## Documentation rules
### README.md
Ensure it contains:
- project purpose
- architecture summary
- main functions
- driver overview
- setup steps
- usage examples
- only verified stack/version/tooling claims

### DevelopmentGuide.md
Ensure it contains:
- developer workflow
- file/module layout
- driver notes
- lint/test commands
- Raspberry Pi validation flow
- common troubleshooting notes
- public exports and CLI surfaces that match the code

### DevelopmentLog.md
Append a dated entry with:
- task summary
- files changed
- why the change was made
- lint/test results
- Raspberry Pi validation status
- follow-up work

### InstallationGuide.md
Ensure it is updated when user-visible setup changes, including:
- wiring assumptions
- required system packages or services
- calibration order
- config import/export steps
- first-run validation steps

### Package README
Ensure the affected package README reflects:
- package root exports
- CLI commands and examples
- config file names and defaults
- actual current runtime behavior
- troubleshooting and validation notes

## Completion rule
If code changed and docs were not reviewed, the task is not complete.
If docs changed, they are not complete until they have been fact-checked against the code.

## Tone and style
- Always provide clear step-by-step instructions for setup, testing, and validation.
- Give concise explanations of each step's purpose and expected outcome.
- Use wording that is understandable to non-developer users. If any professional jargon or abbreviations are necessary, explain them in simple terms.
- If any code examples are included, ensure they are copy-paste ready and well-commented for clarity.
- If the same information appears in English, Japanese, and Traditional Chinese docs, keep those sections synchronized or explicitly note what still needs translation.
- Never state that Raspberry Pi validation or test execution happened unless it actually happened.
