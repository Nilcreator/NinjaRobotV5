---
type: Entity
title: ninja_webapp Package
description: Mobile-first React 18 SPA frontend providing real-time controls, AI chat,
  telemetry, and internationalization.
status: stable
generated:
  by: antigravity-agent/1
  at: '2026-08-22T14:22:00Z'
sources:
- id: src-20260822-developmentguide
  resource: urn:llmwiki:source:src-20260822-developmentguide
  title: NinjaRobot V5 Development Guide
  content_hash: sha256:26272dce2ec7dcab9f3181e1ce0621448ef12547ff26f3b7a0ac4fc50cef9b4d
- id: src-20260822-readme
  resource: urn:llmwiki:source:src-20260822-readme
  title: NinjaRobot V5 Readme
  content_hash: sha256:747c8c2e1e67d24b5d6f6b9c797a6eb7ec7b92b1ce4368623cc9b77b62c442a4
semantic_review:
  version: 1
  performed_by: agent:codex
  performed_at: '2026-09-01T07:28:37Z'
  target_hash: sha256:93971670e3c9c58a8565c4860632c11ef5e0ec689f677fe9f3280cf0f41c6b19
  result: passed
  checks:
    source_support: passed
    contradictions: passed
    limitations: passed
    claim_strength: passed
    visual_evidence: not_applicable
  notes:
  - React/Vite, web transport, telemetry, and multilingual UI claims are supported without claiming complete
    translation coverage.
---

# ninja_webapp Package

`ninja_webapp` is the modern web frontend for NinjaRobot V5, built with React 18, Vite, and `react-router-dom`.[^src-20260822-readme] [^src-20260822-developmentguide]

## Architecture & Technology

* **Framework**: React 18 + Vite.[^src-20260822-developmentguide]
* **Styling**: Vanilla CSS with curated responsive tokens and modern micro-animations.[^src-20260822-developmentguide]
* **Internationalization**: `react-i18next` translations for English (`en`), Japanese (`ja`), Traditional Chinese (`zh-tw`), and Simplified Chinese (`zh-cn`).[^src-20260822-readme] [^src-20260822-developmentguide]
* **Real-Time Communication**: WebSocket connection (`/ws/events`) streaming distance telemetry, execution logs, and robot status.[^src-20260822-developmentguide]

## Application Pages

* **Home (`/`)**: Hero branding display and interactive slide-to-confirm power-off slider for safe robot shutdown.[^src-20260822-developmentguide]
* **Agent (`/agent`)**: Main control dashboard featuring:
  * **AI Chat Dialog**: Conversational text and voice input with Google Gemini.[^src-20260822-readme] [^src-20260822-developmentguide]
  * **Hardware Quick Controls**: Direct triggering of facial expressions, sounds, and recorded movements.[^src-20260822-developmentguide]
  * **Real-Time Telemetry**: Distance sensor reading display with safety indicators.[^src-20260822-readme] [^src-20260822-developmentguide]
  * **Slidable System Log Panel**: Real-time log monitor for debugging and telemetry.[^src-20260822-developmentguide]
* **Help (`/help`)**: User manual and quick reference documentation.[^src-20260822-developmentguide]

[^src-20260822-developmentguide]: NinjaRobot V5 Development Guide.
[^src-20260822-readme]: NinjaRobot V5 Readme.
