---
type: Directory Index
title: Agent Playbooks & Runbooks
description: Index of operational prompts and execution frameworks for autonomous astrological agents.
tags: [index, agents, playbooks, prompts, operations]
timestamp: 2026-07-01T12:00:00Z
---

# Agent Playbooks

This directory contains the standard operating procedures (SOPs) and instructions for AI agents interacting with this knowledge base. 

## Operational Frameworks

* **[Astrology Writer](../astrology-writer/SKILL.md)**: **Primary operational guide for chat interfaces** (LM Studio, local 4B–9B models). Contains the complete decoding key, pre-flight self-check protocol, and navigation network for interactive turn-by-turn chart consultations using `*_llm_context.md`.
* **[Astrology Report Gatekeeper](../astrology-report-gatekeeper/SKILL.md)**: **In-memory quality-assurance gatekeeper**. Intercepts draft readings, executes a 4-point verification against source context files, and auto-corrects any errors before chat output.
* **[3-Phase Synthesis Agent](./3_phase_synthesis_agent.md)**: The structured 3-phase execution framework for delivering complete, multi-phase chart synthesis directly in the chat window.

## Standard Astrological Artifacts
The astrological engine and knowledge base operate on four standardized artifact types:
* `[subject]_astrology_profile.json` — Comprehensive calculation engine profile (v2.0)
* `[subject]_llm_payload.json` — Pruned JSON payload optimized for LLM tool consumption
* `[subject]_llm_context.md` — Condensed markdown context sheet for prompt injection and chat consultants
* `[subject]_report.html` — Full interactive visual report

> [!IMPORTANT]
> **Direct Chat Output Rule:** Models must print all interpretations, briefings, and analyses directly to the active chat window. Do NOT call file creation tools or attempt to write files to disk.