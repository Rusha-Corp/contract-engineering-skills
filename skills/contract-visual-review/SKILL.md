---
name: contract-visual-review
description: Review offline Contract Engineering visual artifacts safely.
---

# Contract Visual Review

Review canonical HTML, Mermaid, SVG, and tradeoff artifacts from a local
preview only. Validate the artifact manifest before serving it.

- Require localhost-only serving and offline assets.
- Reject scripts, event handlers, remote URLs, forms, storage access, and
  external SVG references.
- Compare source and derived artifact hashes.
- Record visual review findings; never mark a design approved or admit a
  packet.
