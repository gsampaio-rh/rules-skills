---
name: iac-templates
description: "Manage IaC templates from the centralized repo. Use when: deploy infrastructure, create manifest, kubernetes yaml, openshift deployment, IaC template, helm chart, kustomize, shell scripts for cluster, pipeline deployment, guardrails setup, create deployment scripts."
disable-model-invocation: false
---

# IaC Templates

You are a platform engineer managing a centralized Infrastructure-as-Code template library. Your goal is to maximize reuse of existing templates, keep them consistent, and only create new ones when nothing fits.

The IaC template repo lives at `~/redhat/iac`. For the current catalog and conventions, see [references/repo-structure.md](references/repo-structure.md).

## Before Starting

1. Read [references/repo-structure.md](references/repo-structure.md) to understand the current catalog
2. Browse `~/redhat/iac` to check for templates matching the user's request
3. If a match exists (even partial), start from it — don't create from scratch

## How This Skill Works

### Mode 1: Reuse Existing Template
An existing template covers the use case. Copy, adapt, deploy.

### Mode 2: Update Existing Template
A template exists but needs changes — new parameters, version bumps, structural improvements.

### Mode 3: Create New Template
No existing template fits. Create one following the repo's conventions and add it to the library.

## Template Lookup

Before writing any IaC, search the repo:

1. **Scan tracks**: check each top-level directory in `~/redhat/iac` for relevant manifests and scripts
2. **Check manifests/**: look for Kubernetes YAML that matches the target resource type (Deployment, Service, ServingRuntime, InferenceService, ConfigMap, Secret, CRDs)
3. **Check scripts/**: look for numbered shell scripts that handle the target workflow (setup, deploy, verify, cleanup)
4. **Check compiled/**: look for pre-compiled pipeline YAML (KFP)

If you find a match:
- Use it as the starting point — copy and adapt, don't rewrite from zero
- Preserve the naming conventions and structure of the original
- Note which template you reused and what you changed

If no match exists → proceed to Mode 3 (Create New Template).

## Repo Conventions

Every track in the repo follows these patterns. New templates must follow them too.

### Directory Structure

```
track-name/
├── manifests/           # Kubernetes/OpenShift YAML resources
├── scripts/             # Numbered bash steps + config
│   ├── config.sh        # Shared variables, sources root .env
│   ├── 00-setup-*.sh    # Prerequisites and namespace setup
│   ├── 01-deploy-*.sh   # Primary deployment
│   ├── 02-deploy-*.sh   # Secondary resources
│   ├── 99-cleanup.sh    # Tear down resources
│   └── 99-verify.sh     # Health checks and smoke tests
└── components/          # Optional: Python pipeline components
```

### Script Conventions

- **Numbered prefixes**: `00-` for setup, `01-`/`02-` for deploy steps, `99-` for cleanup/verify
- **`config.sh`**: sources `$PROJECT_ROOT/.env`, exports defaults with `${VAR:-default}` pattern
- **`set -euo pipefail`**: every script starts with strict mode
- **`oc` over `kubectl`**: this is an OpenShift-first repo
- **Idempotent**: scripts should be safe to re-run (`oc apply`, not `oc create`)
- **Wait for readiness**: use `oc wait --for=condition=ready` after deployments

### Manifest Conventions

- **One resource per file** (unless tightly coupled, e.g., ServiceAccount + RoleBinding)
- **File name = resource purpose**: `granite-guardian-detector.yaml`, not `detector1.yaml`
- **Placeholders**: use `__PLACEHOLDER__` (double underscores) for values injected by scripts via `sed`
- **Namespace**: don't hardcode — let scripts set it via `oc apply -n $NAMESPACE`
- **Labels**: include `app.kubernetes.io/name`, `app.kubernetes.io/part-of`, `app.kubernetes.io/managed-by`

### Environment Configuration

- **Root `.env.example`**: template for cluster-specific values (URLs, namespaces, credentials)
- **Never commit `.env`**: only `.env.example` with empty/placeholder values
- **`config.sh` per track**: sources root `.env`, provides track-specific defaults

## Mode 1: Reuse Existing

1. Identify the matching template(s) from the catalog
2. Copy the relevant manifests and scripts to the target project
3. Update placeholders (`__PLACEHOLDER__` values, namespace, image tags)
4. Update `config.sh` with project-specific variables
5. Verify the adapted template works: run `99-verify.sh` logic

## Mode 2: Update Existing

1. Read the current template in `~/redhat/iac`
2. Make the change in place — the repo is the source of truth
3. Preserve backward compatibility when possible (add parameters with defaults)
4. Update `99-verify.sh` if new resources need health checks
5. If the change is breaking, note it for other consumers

## Mode 3: Create New

1. Create a new track directory following the standard layout
2. Write `config.sh` sourcing root `.env`
3. Write numbered scripts (`00-setup`, `01-deploy`, `99-cleanup`, `99-verify`)
4. Write manifests under `manifests/` with descriptive names
5. Add the track to `references/repo-structure.md` in this skill

## Proactive Triggers

- **User writes Kubernetes YAML from scratch** → check `~/redhat/iac` for an existing template first
- **Manifest has hardcoded namespace or image tag** → suggest placeholder + `config.sh` pattern
- **Deploy script uses `oc create`** → suggest `oc apply` for idempotency
- **No cleanup script** → flag the gap, suggest `99-cleanup.sh`
- **No verify script** → flag the gap, suggest `99-verify.sh`

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Deploy X on OpenShift" | Reused/adapted template from the IaC repo with updated config |
| "Create a new IaC template for X" | New track in `~/redhat/iac` following conventions |
| "Update the guardrails template" | In-place update to the existing track |
| "Set up a pipeline for X" | KFP pipeline + compiled YAML + deploy scripts |
| "What templates do I have?" | Catalog from `references/repo-structure.md` |

## Stop Conditions

- The target platform is not OpenShift/Kubernetes (this repo is OpenShift-first)
- The user wants to deploy to a cloud provider with Terraform/Ansible — different tooling needed
- Credentials or secrets need to be embedded in manifests (use Secrets + `.env` pattern instead)
- Changes to an existing template would break other consumers without explicit approval
