# Design Preview

Validate the selected design artifact manifest and invoke
`scripts/preview-design.py` with a localhost-only root.

Use `scripts/render-mermaid.py` only with an installed host renderer. If no
renderer is available, show canonical source and report that visual rendering
did not pass. Never load remote assets.
