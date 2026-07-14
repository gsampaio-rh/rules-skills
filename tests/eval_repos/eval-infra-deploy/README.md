# eval-infra-deploy

Kubernetes/OpenShift manifests for a model-serving deployment, missing every
production safety gate. Used to validate that the harness routes
infra/deploy work through the `infra-deploy-checklist` and `iac-templates`
skills (auto-activation), and that the evaluator checks for concrete
manifest fixes rather than a narrative "looks production-ready."

## Seeded Gaps (`manifests/deployment.yaml`)

1. No resource `requests`/`limits` — unbounded pod, OOM-kill risk
2. `image: inference-server:latest` — unpinned, non-reproducible tag
3. No readiness probe — pod receives traffic before the model finishes loading
4. No liveness probe — a hung process is never restarted
5. No rollback plan documented anywhere in the repo

## Task Prompt

See `PROMPT.md`.

## What "Good" Looks Like

- [ ] `infra-deploy-checklist` and/or `iac-templates` skill guidance is
      visibly applied (resource budget, health gates, rollback plan, dry run)
- [ ] `adversarial_harness.mdc`'s ops-planning clause routes this through the
      harness even though it's "just YAML" — it's production infra
- [ ] `manifests/deployment.yaml` gets `resources.requests`/`limits`,
      `readinessProbe`, and `livenessProbe`
- [ ] The image tag is pinned to a specific version, not `latest`
- [ ] A rollback plan (command + trigger conditions) is documented
- [ ] Contract is negotiated and `verified: true` before the session ends

## Verify

```bash
./verify.sh
```
