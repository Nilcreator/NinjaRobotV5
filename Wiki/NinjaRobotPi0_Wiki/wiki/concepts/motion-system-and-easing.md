---
type: Concept
title: Motion System and Easing Curves
description: Velocity-based physics motion calculations, position-aware easing curves,
  and the movement command syntax.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-readme-7
  resource: urn:llmwiki:source:src-20260822-readme-7
  title: pi0servo Readme
  content_hash: sha256:23793729576aa0b8f5b460d7fe4e47ab1d7ad4f9a6af4348bf4c8208a6610a76
- id: src-20260822-readme-3
  resource: urn:llmwiki:source:src-20260822-readme-3
  title: ninja_core Readme
  content_hash: sha256:4c4bc38f4de4851f444770bd63e6214e5d04a4ee12d30f0d8b0b2a5b5a453471
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:374bb5c44297ceb5134e5c4558f07d84378db45ea18ece6cdc3ecf3319a08e85
semantic_review:
  version: 1
  performed_by: agent:antigravity
  performed_at: '2026-08-23T01:00:00Z'
  target_hash: sha256:9ff6bbe478d4c15c9736fa67ba135820e03a75d2ac3904e413467c9883e8d8c3
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - Velocity-based kinematic motion model, position-aware cubic easing, and calibration
    limits match pi0servo documentation.
---

# Motion System and Easing Curves

The NinjaRobot V5 motion system operates on physics-based velocity control rather than fixed duration steps, providing smooth, jitter-free movement for up to 8 servo motors simultaneously.[^src-20260822-readme-7] [^src-20260822-developmentguide]

## Velocity-Based Control Architecture

Traditional hobby robotics controls servos with arbitrary `time.sleep()` delays between target positions.[^src-20260822-developmentguide] In contrast, `pi0servo` computes step deltas based on target angular velocity (°/sec) and a fixed **100Hz update frequency** (10ms step intervals):[^src-20260822-readme-7]

* **Speed Modes**:
  * `F` (Fast): Maximum velocity for rapid gestures.[^src-20260822-readme-7]
  * `M` (Medium): Balanced speed (default).[^src-20260822-readme-7]
  * `S` (Slow): Gentle, high-torque positioning.[^src-20260822-readme-7]
* **Per-Servo Speed Limits**: Configurable in `servo.json` (0–100%) to protect delicate mechanical linkages.[^src-20260822-readme-7]
* **Thread-Safe Abort**: Calling `ServoGroup.abort()` immediately terminates active trajectory loops from external event threads or safety monitors.[^src-20260822-readme-7]

## Position-Aware Multi-Step Easing

In multi-step sequence playbacks (e.g., walking or waving), traditional easing causes awkward stop-start hesitations between waypoints.[^src-20260822-readme-3] [^src-20260822-developmentguide] `MovementController` solves this by applying **position-aware easing**:[^src-20260822-readme-3] [^src-20260822-developmentguide]

```
Sequence Step:    [ Step 1 (Start) ]  ──▶  [ Step 2..N-1 (Waypoints) ]  ──▶  [ Step N (End) ]
Applied Easing:     ease_in_cubic                   linear                     ease_out_cubic
Behavior:          Accelerate only             Constant velocity             Decelerate to stop
```

This preserves momentum across waypoints and creates fluid, organic motion.[^src-20260822-readme-3]

## Movement Command Syntax

Motion steps are defined using a compact string syntax supported by CLI tools and the web interface:[^src-20260822-readme-7] [^src-20260822-readme-3]

```
[GLOBAL_SPEED_]PIN:ANGLE[LOCAL_SPEED][/PIN:ANGLE[LOCAL_SPEED]...]
```

* **Basic Move**: `20:45` (move GPIO 20 to 45° at Medium speed).[^src-20260822-readme-7]
* **Angle Keywords**: `C` (Center, 0°), `M` (Min, -90°), `X` (Max, 90°).[^src-20260822-readme-3]
* **Multi-Servo Step**: `M_20:45/21:-30/22:C` (simultaneous move across 3 servos).[^src-20260822-readme-7]
* **Speed Overrides**: `S_20:C/21:XF` (global Slow, but pin 21 moves Fast).[^src-20260822-readme-7]
* **Position Auto-Completion**: If a servo pin is omitted in a step, it retains its previous angle, allowing concise sequence scripts.[^src-20260822-readme-3]

[^src-20260822-readme-7]: pi0servo Readme.
[^src-20260822-readme-3]: ninja_core Readme.
[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
