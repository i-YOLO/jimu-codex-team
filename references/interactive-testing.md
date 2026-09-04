# Interactive Testing

Read this reference only when real UI, browser, device, account, or external interactive state is required and code inspection or automated tests cannot provide credible evidence.

## Operator Rules

- Give repeatable, bounded, observable interaction paths to `Frontend`, `FrontendFast`, or `Executor` when the assigned slice requires UI interaction.
- Keep product tradeoffs, subjective visual judgment, weak oracles, and final experience acceptance in the main thread.
- Allow only one active operator per shared browser session, device, account, or external environment.
- Parallelize only when environments and mutable state are genuinely isolated.

## Dispatch Additions

In addition to the standard packet, state:

- `Scenario`: user goal and starting state.
- `Environment`: browser, device, account, data, and permission boundary.
- `Actions`: minimum necessary interaction path.
- `Oracle`: observable success, failure signals, and allowed tolerance.
- `Evidence`: smallest sufficient screenshots, logs, recording, or state snapshots.
- `Cleanup`: how temporary data and state are restored.

Reuse facts already established by code checks and automated tests. If the environment is unavailable, state is uncertain, or the oracle is insufficient, return a blocker rather than guessing success.
