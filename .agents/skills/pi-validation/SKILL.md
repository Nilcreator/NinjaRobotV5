---
name: pi-validation
description: Use after hardware-facing or deployment-relevant changes to generate or record Raspberry Pi Zero 2W validation steps, expected outcomes, safety notes, execution status, and a concise pass/fail report.
---

# Pi Validation Report

Use this skill after code changes that may affect Raspberry Pi behavior, hardware drivers, GPIO, I2C, SPI, serial, PWM, sensors, motors, displays, buzzers, servos, startup behavior, deployment setup, or config import/setup flow.

## Required inputs before writing the report

Capture these first:

- what changed
- which packages or files were affected
- which hardware components are involved
- which checks were actually executed on Raspberry Pi Zero 2W
- which checks are still planned but not yet run
- any safety or power risks
- any rollback or recovery steps already known

## Output format
Produce a validation plan with these sections:

1. Scope of validation
2. Environment and prerequisites
3. Safety notes
4. Safe smoke tests
5. Communication/interface tests
6. Sensor/display checks
7. Actuator-moving or power-risk tests
8. Expected outcomes
9. Execution status and evidence
10. Pass/fail checklist
11. Rollback steps

## Rules
- Separate non-moving tests from actuator-moving tests.
- Call out any command that may energize hardware or move an actuator.
- Prefer short, copy-paste-ready commands.
- State what success looks like for each test.
- If the implementation changed deployment assumptions, include environment/setup checks.
- Explicitly separate:
  - tests that were already executed
  - tests that are still recommended but pending
- Never imply that Raspberry Pi validation happened if it was not actually run.
- If multiple libraries are affected, group validation by library or subsystem.
- Mention config files, startup steps, and import/export flows when they matter to reproducing the result.
- If a test could stress power, servo travel, brightness, or buzzer output, say so plainly.
