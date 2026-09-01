# Evaluator Testing Methods by Domain

Load when Mode 2 needs a domain playbook. Prefer the section that matches the contract.

## Web Applications

- Use browser tools to navigate to the app
- Click every interactive element mentioned in criteria
- Type into inputs, submit forms, trigger all user flows
- Open browser console — any error is a finding
- Check network requests for failures
- Test at different viewport sizes if responsiveness is a criterion
- Evidence: `browser_snapshot` YAML (roles, names, text, URL, control state). Spatial: bounding box or CDP `getComputedStyle` — not pixels. Screenshot only when the criterion is visual and snapshot/CDP cannot falsify it.

## CLI / Backend / APIs

- Run the actual commands or API calls
- Test with valid inputs first, then invalid inputs
- Check error messages are helpful, not stack traces
- Verify output format matches expectations
- Test concurrent access if relevant

## Data / ML / Notebooks

- Run the pipeline or notebook end-to-end
- Verify output shapes, types, and value ranges
- Check for NaN propagation and data leakage
- Test with edge-case data: empty, single-row, extreme values
- Verify reproducibility with fixed seeds

## Configuration / Documentation

- Read each file and verify content against criteria
- Grep for prohibited patterns
- Check cross-references between files are consistent
- Verify templates are valid and parseable
- Check that instructions don't contradict each other
