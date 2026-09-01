# Visual Identity: Contract Spark

The Contract-Driven Engineering protocol uses a playful, recognizable visual
identity called **Contract Spark**. The identity is designed to be
self-contained, accessible, and dependency-free.

## Concept

Contract Spark combines three ideas:

- **Linked contract loops** — four interlinked circles representing the
  iterative contract cycle: baseline, gates, implementation, and acceptance.
- **Four-point spark** — the circles are arranged at the cardinal points of a
  spark, representing the energy of agreement and the speed of a well-run
  contract.
- **Central check mark** — a white check mark at the center of a deep-navy hub
  represents verified acceptance: a packet is not complete until the receiver
  accepts the handoff.

## Palette

| Color   | Hex       | Role                        |
| ------- | --------- | --------------------------- |
| Navy    | `#173F5F` | Primary text, hub, badge background |
| Blue    | `#20639B` | Secondary structure, badge border |
| Teal    | `#3CAEA3` | Loop (north)                |
| Yellow  | `#F6D55C` | Loop (east)                 |
| Coral   | `#ED553B` | Loop (west)                 |
| White   | `#FFFFFF` | Check mark, badge text      |

All SVGs use only these approved colors plus `none` for transparent fills.

## Assets

Three SVG files live in `assets/contract-spark/`:

| File | Purpose | Dimensions (viewBox) |
| --- | --- | --- |
| `contract-spark-mark.svg` | Compact mark for favicons, avatars, and small surfaces | 64 x 64 |
| `contract-spark-lockup.svg` | Mark plus wordmark for documentation headers and README | 280 x 64 |
| `contract-spark-badge.svg` | Rounded badge for repository and release surfaces | 200 x 80 |

### Validation

Run the SVG asset validator to check all assets for valid XML, accessible
`<title>` and `<desc>`, `viewBox`, no scripts, no external references, and
palette consistency:

```bash
python3 scripts/validate-svg-assets.py assets/contract-spark/
```

## Accessibility

Every SVG includes `<title>` and `<desc>` elements with `role="img"` and
`aria-labelledby` attributes. The mark is legible at 16px (favicon size) and
scales cleanly to larger sizes via the `viewBox` attribute. The check mark
uses a high-contrast white-on-navy combination.

## Reuse rules

- Use the SVGs as-is; do not recolor, stretch, or add gradients.
- Do not embed external fonts, images, JavaScript, or runtime dependencies.
- Keep clear space around the mark equal to at least one loop radius.
- For dark backgrounds, use the badge variant which has its own navy
  background.
- The wordmark uses `sans-serif` as a generic system font family; no custom
  font is required.

## Size guidance

| Surface | Recommended asset | Notes |
| --- | --- | --- |
| Favicon (16px) | mark | The four loops and central check remain recognizable |
| Avatar / icon (32-64px) | mark | Scales cleanly from the 64px viewBox |
| README header | lockup | Mark plus full wordmark |
| Release badge | badge | Self-contained navy background for any surface |
| Print / large display | mark or lockup | Vector SVG scales to any size |
