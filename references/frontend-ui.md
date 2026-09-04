# Frontend UI Dispatch

Read this reference only when dispatching `Frontend` or `FrontendFast`.

## Model selection

- `Frontend` (`gemini-3.8-flash`) is the normal frontend role and should be used for frontend work by default, including new pages, cross-component work, responsive or multi-state work, client integration, and any visual ambiguity.
- `FrontendFast` (`gemini-3.7-flash`) is supplementary only. Use it exceptionally when the design system and API contract are fixed, the edit is very localized and low-risk, target files are known, deterministic checks exist, and the smaller route has a material speed or cost benefit.
- When uncertain, choose `Frontend`. `FrontendFast` is neither a failure fallback nor a concurrent takeover of a slice already owned by another role.

## Boundary

Assign one complete, independently verifiable frontend slice with its target screens, states, files, and acceptance checks. The role owns the slice end to end within that boundary and preserves unrelated work already in the workspace.

- Reuse the existing design system, tokens, components, accessibility patterns, and responsive conventions.
- The complete frontend scope may include pages, components, styles, interactions, client state, routes, consumption of fixed APIs, assets, and focused frontend tests inside the assigned slice.
- Do not change backend code, database schemas or migrations, authentication or authorization, API contracts, endpoint payloads, generated contracts, or server configuration.
- Do not spawn descendants or publish/deploy externally. If the slice needs a contract change, stop and return the concrete mismatch and blocker to the parent.

## Checks and evidence

Run every project check named in the packet (for example, focused tests, lint, typecheck, and build). Standard visual acceptance, when rendered behavior or layout is in scope, covers the project-defined desktop and mobile viewports plus each relevant default, loading, empty, error, and interactive state that is actually in scope. Provide the smallest useful local preview or screenshot evidence with viewport, route, state, and relevant interaction recorded. The main thread keeps final visual and UX acceptance. If visual evidence cannot be produced, state the exact environment or oracle gap instead of claiming visual verification.

## Return

Return the changed files, checks with exact results, visual evidence and states when applicable, and remaining risks. Report contract, scope, permission, or acceptance blockers without implementing them.
