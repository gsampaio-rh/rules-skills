# IaC Template Catalog

Current inventory of `~/redhat/iac`. Updated as new tracks are added.

## Repository Layout

```
~/redhat/iac/
├── .env.example                    # Cluster-specific config template
├── pipelines/                      # KFP evaluation pipelines
├── trustyai-guardrails/            # TrustyAI operator + ML detectors
└── nemo-guardrails/                # NeMo Guardrails + Nemotron models
```

## Tracks

### `trustyai-guardrails/`

TrustyAI Guardrails orchestrator with ML-based detectors on OpenShift AI.

**Manifests:**
| File | Resource Type | Purpose |
|---|---|---|
| `guardrails-orchestrator.yaml` | `GuardrailsOrchestrator` (CRD) | Orchestrator with gateway config |
| `orchestrator-config.yaml` | `ConfigMap` | Orchestrator routing and detector wiring |
| `gateway-config.yaml` | `ConfigMap` | Gateway endpoint configuration |
| `granite-guardian-detector.yaml` | `ServingRuntime` + `InferenceService` | Granite Guardian safety model |
| `hap-detector.yaml` | `ServingRuntime` + `InferenceService` | Hate/Abuse/Profanity detector |
| `llama-guard-detector.yaml` | `ServingRuntime` + `InferenceService` | Llama Guard safety model |
| `prompt-injection-detector.yaml` | `ServingRuntime` + `InferenceService` | Prompt injection detection |
| `promptguard-detector.yaml` | `ServingRuntime` + `InferenceService` | PromptGuard model |
| `detector-model-storage.yaml` | `PVC` / storage | Shared model storage for detectors |

**Scripts:** `00-setup-namespaces.sh` → `01-deploy-model-server.sh` → `02-deploy-guardrails.sh` → `03-deploy-ml-detectors.sh` → `99-cleanup.sh` / `99-verify.sh`

---

### `nemo-guardrails/`

NVIDIA NeMo Guardrails with Nemotron safety models.

**Manifests:**
| File | Resource Type | Purpose |
|---|---|---|
| `nemo-guardrails-server.yaml` | SA + RoleBinding + ConfigMap + Deployment | NeMo Guardrails server with inline config |
| `nemoguard-jailbreak-detector.yaml` | `ServingRuntime` + `InferenceService` | NeMo jailbreak detection NIM |
| `nemotron-safety-detector.yaml` | `ServingRuntime` + `InferenceService` | Nemotron content safety NIM |
| `nemotron-safety-guard-8b.yaml` | `ServingRuntime` + `InferenceService` | Nemotron Safety Guard 8B model |

**Config:** `config/config.yml` (models + rails), `config/prompts.yml`, `config/rails.co` (Colang flows), `config/actions.py`

**Scripts:** `00-setup-prerequisites.sh` → `01-deploy-nemotron.sh` → `02-deploy-nemo-guardrails.sh` → `99-cleanup.sh` / `99-verify.sh`

---

### `pipelines/`

Kubeflow Pipelines (KFP v2) for guardrails evaluation.

**Pipeline:** `guardrails_eval_pipeline.py` → compiles to `compiled/guardrails_eval_pipeline.yaml`

**Components:**
| File | Purpose |
|---|---|
| `components/load_dataset.py` | Load evaluation dataset from ConfigMap |
| `components/run_evaluation.py` | Run prompts through guardrails endpoints |
| `components/compute_metrics.py` | Calculate precision, recall, F1 |

**Manifests:** `manifests/guardrails-eval-secrets.yaml` (template Secret for routes/tokens)

**Scripts:** `00-setup-pipeline-server.sh` → `01-upload-pipeline.sh` → `99-cleanup.sh` / `99-verify.sh`

**Dependencies:** `requirements.txt` (`kfp`, `kfp-kubernetes`)

---

## Common Patterns

### Resource Types in Use

| Kind | API Group | Tracks |
|---|---|---|
| `GuardrailsOrchestrator` | `trustyai.opendatahub.io/v1alpha1` | trustyai-guardrails |
| `ServingRuntime` | KServe | trustyai-guardrails, nemo-guardrails |
| `InferenceService` | KServe | trustyai-guardrails, nemo-guardrails |
| `ConfigMap` | core/v1 | all |
| `Secret` | core/v1 | pipelines |
| `PersistentVolumeClaim` | core/v1 | trustyai-guardrails |
| `Deployment` | apps/v1 | nemo-guardrails |

### Placeholder Pattern

Scripts use `sed` to inject values from `.env` into manifests at deploy time:

```bash
sed "s|__MODEL_HOSTNAME__|${MODEL_HOSTNAME}|g" "$MANIFEST_DIR/orchestrator-config.yaml" | oc apply -n "$NAMESPACE" -f -
```

### Environment Variables (from `.env.example`)

Key variables across tracks: cluster URLs, namespaces, model endpoints, route hostnames, Keycloak credentials, MinIO/DSPA config.
