# React Docs (Curated)

Source URL:
- https://react.dev/learn

Snapshot date: 2026-04-25
Category: Frontend UI framework documentation

## What This Documentation Covers

React Learn docs explain component-based UI development with JSX, props/state, event handling, and state architecture patterns such as lifting state up.

## Core Concepts

- Components: UI built from reusable function components.
- JSX: JavaScript syntax extension for declarative UI markup.
- Props: parent-to-child data flow.
- State and hooks: local component state with hooks such as `useState`.
- Rendering patterns: conditional rendering and list rendering with stable keys.
- Event handling: connect user interactions to state transitions.
- State architecture: move shared state upward when sibling components must sync.

## Typical Developer Workflow

1. Build small presentational components.
2. Pass data via props and render dynamic values in JSX.
3. Add local state and event handlers.
4. Use conditional/list rendering for real data scenarios.
5. Lift state to common parents when shared behavior is needed.

## Practical Integration Notes

- Use stable keys for list items to avoid UI reconciliation issues.
- Keep component state minimal and derive computed values when possible.
- Separate UI concerns from data-fetching/business logic when app complexity grows.
- Keep component boundaries explicit to reduce unintended re-renders.

## Retrieval Hints

This note is useful when queries mention:
- JSX
- props and state
- hooks
- conditional rendering
- list keys
- lifting state up
