# Anthropic Claude Docs (Curated)

Source URLs:
- https://platform.claude.com/docs/en/docs
- https://platform.claude.com/docs/en/get-started

Snapshot date: 2026-04-25
Category: AI model API and managed agent platform

## What This Documentation Covers

Claude docs explain how to send your first request, use the Messages API, compare models, and build production integrations with SDKs and platform features.

## Core Concepts

- API key setup: configure `ANTHROPIC_API_KEY` in your environment.
- Messages API: requests typically include model, token budget, and a message list.
- Conversation structure: multi-turn workflows and prompt/system control.
- Model choice: pick model family by reasoning depth, speed, and cost.
- Capability expansion: tools, context management, structured outputs, and other platform features.

## Typical Developer Workflow

1. Create Anthropic account and API key.
2. Install SDK (Python or TypeScript are common starts).
3. Send first Messages API call.
4. Add multi-turn context and system-level behavior shaping.
5. Evaluate model/cost trade-offs and add reliability controls.

## Practical Integration Notes

- Keep credentials outside source code.
- Capture stop reasons and response metadata for debugging.
- Validate output format when downstream systems expect strict structure.
- Compare direct API usage vs managed agent offerings for async tasks.

## Retrieval Hints

This note is useful when queries mention:
- Claude Messages API
- Anthropic SDK
- model comparison
- stop reasons
- context management
- structured outputs
