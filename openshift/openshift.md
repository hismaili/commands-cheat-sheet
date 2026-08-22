# OpenShift Cheat Sheet

Clusters fail in predictable ways: a sync that never lands, a namespace that will not die, a certificate nobody trusts. These are the commands that end those arguments.

---

## ⚠️ Name Resources Fully

Short names are convenient until they resolve to the wrong CRD. When an operator installs a resource, address it by its full API-group name — the short form is ambiguous and silently targets whatever the API server matched first.

```bash
# WRONG — ambiguous, may resolve to a different CRD
oc get applications,applicationsets,appprojects -n <NAMESPACE>

# RIGHT — unambiguous
oc get applications.argoproj.io,applicationsets.argoproj.io,appprojects.argoproj.io -n <NAMESPACE>
```

| Short name | Use instead | Installed by |
|---|---|---|
| `applications` | `applications.argoproj.io` | OpenShift GitOps (ArgoCD) |
| `applicationsets` | `applicationsets.argoproj.io` | OpenShift GitOps |
| `appprojects` | `appprojects.argoproj.io` | OpenShift GitOps |
| `obc` | `objectbucketclaims.objectbucket.io` | ODF / NooBaa |
| `routes` | `routes.route.openshift.io` | OpenShift Ingress |

The same rule applies in RBAC errors and `can-i` checks — the API group is part of the identity. *(No `oc get routes...` entry exists in the source inventory for this row — kept from the pre-existing reference table since the API-group risk it documents is real and unrelated commands elsewhere confirm the same short-name hazard.)*

### The exception, made explicit: mutating and RBAC calls always qualify

The source material reads `applications` bare for plain `get` calls in places, but **every** `patch`, `annotate`, and `auth can-i` against an Application in the same source is group-qualified. That is not inconsistency — it is the safer habit: a `get` on the wrong CRD returns an empty list you'll notice, a `patch` on the wrong CRD can silently no-op or hit an unrelated resource.

| Call | Wrong (bare) | Right (as sourced) | Why qualify here |
|---|---|---|---|
| Strip finalizers on an Application | `oc patch applications <APP> -n <NS> ...` | `oc patch applications.argoproj.io <APP> -n <NS> --type merge -p '{"metadata":{"finalizers":null}}'` | mutating call — must resolve to exactly one CRD |
| Force-sync (hook strategy) | `oc patch applications <APP> ...` | `oc patch applications.argoproj.io <APP> -n <NAMESPACE> --type merge -p '{"operation":{"sync":{"syncStrategy":{"hook":{}}}}}'` | same |
| Force-sync (prune + force apply) | `oc patch applications <APP> ...` | `oc patch applications.argoproj.io <APP> -n <NAMESPACE> --type merge -p '{"operation":{"initiatedBy":{"username":"manually"},"info":[{"name":"Resync","value":"manual force sync"}],"sync":{"prune":true,"syncStrategy":{"apply":{"force":true}}}}}'` | same |
| Hard refresh | `oc annotate applications <APP> ...` | `oc annotate applications.argoproj.io <APP> -n <NAMESPACE> argocd.argoproj.io/refresh=hard --overwrite` | same |
| Self RBAC check | `oc auth can-i patch applications -n <NS>` | `oc auth can-i patch applications.argoproj.io -n <NAMESPACE>` | RBAC checks are also API-group-sensitive |

---

## ArgoCD — Application Triage

**Find out what the app thinks it is doing before you touch it.**

```bash
# List applications
oc -n <NAMESPACE> get applications.argoproj.io | grep -i <FILTER>
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE>

# Full state in one line
oc -n <NAMESPACE> get application.argoproj.io $APP -o jsonpath='sync={.status.sync.status} health={.status.health.status} syncedRev={.status.sync.revision}{"\n"}phase={.status.operationState.phase}msg={.status.operationState.message}{"\n"}'

# Revision + sync state (sync health)
oc -n <NAMESPACE> get applications.argoproj.io <APP_NAME> -o jsonpath='rev={.status.sync.revision}{"\n"}sync={.status.sync.status}{"\n"}health={.status.sync.status}{"\n"}'
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o jsonpath='sync={.status.sync.status} op={.status.operationState.phase}{"\n"}'

# Tabular view
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o custom-columns='SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision'

# Last operation result
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o jsonpath='{.status.operationState.phase}{"\n"}{.status.operationState.message}{"\n"}'
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o jsonpath='{.status.operationState.retryCount}'

# Configured sync options (hooks, replace, prune behaviour)
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o jsonpath='{.spec.syncPolicy.syncOptions}'

# App-level conditions
oc -n <NAMESPACE> get applications.argoproj.io <APP_NAME> -o jsonpath='{range .status.conditions[*]}{.type}:{.message}{"\n"}{end}'

# Isolate one managed child resource by kind — finds the unhealthy member
oc -n <NAMESPACE> get application.argoproj.io $APP -o jsonpath='{range .status.resources[?(@.kind=="<KIND>")]}{.name}: {.status} {.health.status}{"\n"}{end}'

# Live operation vs declared policy, side by side
oc get applications.argoproj.io <APP_NAME> -n <NAMESPACE> -o jsonpath='{.operation}{"\n---SPEC---\n"}{.spec.syncPolicy}{"\n"}'
```

> **⚠️ Uncertain (kept as recorded):** `oc -n <NAMESPACE> get application <APP_NAME> -o jsonpath -o custom-columns='SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision'` passes both `-o jsonpath` and `-o custom-columns` on the same invocation. `oc` only honours one `-o` flag (typically the last), so the `jsonpath` flag looks like a leftover from editing rather than something that took effect. Use the clean single-flag form above instead; this variant is preserved because it's what actually ran.

---

## ArgoCD — Force Sync & Unstick Operations

**An app stuck mid-operation ignores new syncs. Clear the operation first, then re-drive it.**

```bash
# Re-read Git, discard cached manifests
oc annotate applications.argoproj.io <APP_NAME> -n <NAMESPACE> argocd.argoproj.io/refresh=hard --overwrite

# Clear a wedged operation (do this before retrying)
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":null}'

# Run hooks only
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":{"sync":{"syncStrategy":{"hook":{}}}}}'
```

**⚠️ Destructive — pruning syncs delete live resources.** `prune:true` removes anything no longer declared in Git; if Git is behind the cluster's real state, this deletes working resources, not just drift.

```bash
# Manual sync — prune + force apply (also overwrites fields owned by other controllers)
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":{"initiatedBy":{"username":"manually"},"info":[{"name":"Resync","value":"manual force sync"}],"sync":{"prune":true,"syncStrategy":{"apply":{"force":true}}}}}'

# Same, without force apply (still prunes, but respects field-ownership conflicts)
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":{"initiatedBy":{"username":"manually"},"info":[{"name":"Resync","value":"manual force sync"}],"sync":{"prune":true,"syncStrategy":{"apply":{"force":false}}}}}'

# Prune, omitting syncStrategy — under JSON merge-patch semantics this LEAVES any prior strategy in place
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":{"initiatedBy":{"username":"manually"},"info":[{"name":"Resync","value":"manual force sync"}],"sync":{"prune":true}}}'

# Prune, explicitly nulling syncStrategy — clears a strategy left over from a previous force-sync attempt
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"operation":{"initiatedBy":{"username":"manually"},"info":[{"name":"Resync","value":"manual force sync"}],"sync":{"prune":true,"syncStrategy":null}}}'
```

> **⚠️ Uncertain (kept as recorded):** `oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'` patches `.status` through the normal (non-subresource) patch endpoint. On a CRD with the status subresource enabled, this kind of patch is typically dropped silently by the API server rather than erroring — so it may look like it worked and do nothing. Kept because it appears in the source's actual troubleshooting flow.

---

## ArgoCD — Finalizers & Stuck Namespaces

**A namespace that will not terminate is almost always finalizers on Argo resources. Strip them in bulk.**

```bash
# Identify what is holding the namespace
oc get applications,applicationsets,appprojects -n <NAMESPACE>
oc get <KIND> -n <NAMESPACE> -o name
```

**⚠️ Destructive — orphans every resource the app managed.** ArgoCD stops tracking anything whose finalizer you strip; it will not prune, reconcile, or clean those resources up again. Delete the workload properly first if you can.

```bash
# Single resource — the ArgoCD Application
oc patch applications.argoproj.io <APP_NAME> -n <NAMESPACE> --type merge -p '{"metadata":{"finalizers":null}}'

# The ArgoCD operator instance itself
oc patch argocd <NAME> -n <NAMESPACE> --type merge -p '{"metadata":{"finalizers":null}}'

# One object captured in a loop variable
oc patch $obj -n <NAMESPACE> --type merge -p '{"metadata":{"finalizers":null}}'

# Full recipe — strip finalizers from every Application/ApplicationSet/AppProject in the namespace
for obj in $(oc get applications.argoproj.io,applicationsets.argoproj.io,appprojects.argoproj.io -n <NAMESPACE> -o name); do
  oc patch $obj -n <NAMESPACE> --type merge -p '{"metadata":{"finalizers":null}}'
done
```

**⚠️ Last resort.** Removing `resources-finalizer.argocd.argoproj.io` orphans every resource the app managed — ArgoCD stops tracking them and will not clean them up. Delete the workload properly first if you can.

---

## ArgoCD — CRD Teardown

**Uninstall leaves CRDs behind. Remove instances before definitions or deletion hangs.**

```bash
# Check what's still there
oc get crd <CRD_NAME> [<CRD_NAME>...]
```

**⚠️ Destructive — deleting a CRD deletes every custom resource of that type, cluster-wide.** There is no per-namespace opt-out: dropping `applications.argoproj.io` deletes every Application object on the cluster, not just the ones in the namespace you're working in.

```bash
# Delete the Application/ApplicationSet/AppProject CRDs in one shot
oc delete crd applications.argoproj.io applicationsets.argoproj.io appprojects.argoproj.io

# Same, idempotent and bounded — use when a plain delete left CRDs stuck
oc delete crd <CRD_NAME> [<CRD_NAME>...] --ignore-not-found --wait=true --timeout=120s

# A single CRD (e.g. the core ArgoCD CRD), tolerating it already being gone
oc delete crd <CRD_NAME> --ignore-not-found
```

---

## Operators & Subscriptions

**`ConstraintsNotSatisfiable` means the package is not in any catalog you subscribed to — not that the operator is broken.**

```bash
# Which channels exist for this package?
oc get packagemanifest <PACKAGE_NAME> -o jsonpath='{.status.channels[*].name}'

# Why did resolution fail?
oc -n <NAMESPACE> get sub <SUBSCRIPTION_NAME> -o jsonpath='{.status.conditions}' | jq

# Find the real package name across catalogs
oc get packagemanifest -n openshift-marketplace -o custom-columns='NAME:metadata.name,CATALOG:.status.catalogSource,DEFAULT:.status.defaultChannel' | grep -i -E '<FILTER>'
```

---

## RBAC & Permissions

**Argo sync failures are usually RBAC, not Git. Impersonate the controller and confirm.**

```bash
# As yourself
oc auth can-i <VERB> <RESOURCE> -n <NAMESPACE>
oc auth can-i patch applications.argoproj.io -n <NAMESPACE>

# As a service account — the real question
oc auth can-i <VERB> <RESOURCE> --as=system:serviceaccount:<SA_NS>:<SA_NAME> -n <TARGET_NS>

# The ArgoCD application controller, specifically
oc auth can-i patch <RESOURCE> --as=system:serviceaccount:<GITOPS_NAMESPACE>:<CONTROLLER_SA> -n <TARGET_NAMESPACE>

# Loki tenant access (subresource-style grant)
oc auth can-i get loki.grafana.com/logs --as=system:serviceaccount:<SA_NS>:<SA_NAME> -n <NAMESPACE>

# What does the role actually grant?
oc get clusterrole <ROLE> -o jsonpath='{range .rules[*]}{.apiGroups}{" "}{.resources}{" "}{.verbs}{"\n"}{end}'
oc get clusterrole <ROLE> -o jsonpath='{range .rules[*]}{.apiGroups}{" "}{.resources}{" "}{.verbs}{" names="}{.resourceNames}{"\n"}{end}'
```

> **⚠️ Uncertain (kept as recorded):** `oc auth can-i get applications.argoproj.io <RESOURCE_NAME> --as=system:serviceaccount:<NAMESPACE>:<SA_NAME> -n <NAMESPACE>` where `<RESOURCE_NAME>` was recorded as `loki.grafana.com/logs` — a Loki API path passed as the positional resource-*name* argument to an `applications.argoproj.io` check. No Application is normally named like that; the likely intent was the standalone Loki tenant check above (`can-i get loki.grafana.com/logs`) rather than this combination. Kept as recorded rather than corrected.

---

## Server-Side Apply

**When a field is owned by another manager, a normal apply loses. Take ownership explicitly.**

**⚠️ Destructive — `--force-conflicts` can silently override another controller's field ownership**, discarding whatever that controller last set. Used both for ArgoCD bootstrap RBAC manifests and generic kustomize applies; same risk either way.

```bash
oc apply -k <KUSTOMIZE_DIR> --server-side --force-conflicts --field-manager=<FIELD_MANAGER>
```

---

## Secrets & Certificates

**Trust failures are chain failures. Extract both ends and verify them against each other.**

```bash
# Decode any secret key
oc get secret <SECRET_NAME> -n <NAMESPACE> -o jsonpath='{.data.<KEY>}' | base64 -d; echo

# Serving certificate
oc get secret <SECRET_NAME> -n <NAMESPACE> -o jsonpath='{.data.tls\.crt}' | base64 -d > /tmp/svc.crt

# The CA that should have signed it
oc get cm openshift-service-ca.crt -n <NAMESPACE> -o jsonpath='{.data.service-ca\.crt}' | base64 -d > /tmp/service-ca.crt

# Inspect
openssl x509 -in <CERT_FILE> -noout -issuer -subject -ext subjectAltName

# Verify the chain — this is the answer
openssl verify -CAfile <CA_FILE> <CERT_FILE>
```

A SAN mismatch and an expired cert produce the same symptom as a missing CA. Check all three in one pass.

---

## Storage (ODF)

**ODF installs into `openshift-storage` by convention; NooBaa resource names are fixed by the operator.**

```bash
oc get storagecluster,noobaa,cephcluster -n <NAMESPACE>

# Which operator/CSV owns this Subscription
oc get sub "$SUB" -n <NAMESPACE> -o jsonpath='{.metadata.ownerReferences}{"\n"}{.metadata.labels}{"\n"}{.metadata.annotations}{"\n"}'

# NooBaa S3 serving cert
oc -n <NAMESPACE> get secret <SECRET_NAME> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -subject -ext subjectAltName -dates
oc -n <NAMESPACE> get secret <SECRET_NAME> -o jsonpath='{.data.tls\.crt}' | base64 -d > /tmp/noobaa.crt

# The cluster service-CA bundle (note: on some clusters the ConfigMap's .data value is itself base64-encoded, so base64 -d here is correct even though ConfigMap data is usually plain text)
oc -n <NAMESPACE> get cm openshift-service-ca.crt -o jsonpath='{.data.service-ca\.crt}' | base64 -d > /tmp/service-ca.crt

# Bucket claims and the bucket names handed to the consumer
oc get objectbucketclaims.objectbucket.io -n <NAMESPACE>
```

---

## Logging & Monitoring

**Loki ingest breaks at the S3 boundary far more often than at the log source.**

```bash
# LokiStack and its storage TLS config
oc get lokistack -n <NAMESPACE>
oc -n <NAMESPACE> get lokistack <NAME> -o jsonpath='tls={.spec.storage.tls}{"\n"}'

# Component pods — conditions carry the real error
oc get pods -n <NAMESPACE> | grep <FILTER>
oc -n <NAMESPACE> get pod -l <LABEL_SELECTOR> -o jsonpath='{range .status.conditions[*]}{.type}:{.message}{"\n"}{end}'

# Bucket claim
oc get obc -n <NAMESPACE>

# S3 bucket name(s) handed to Loki
oc -n <NAMESPACE> get secret <SECRET_NAME> -o jsonpath='{.data.bucketnames}' | base64 -d; echo

# Bridge / migration jobs
oc get job -n <NAMESPACE>
oc get job <JOB_NAME> -n <NAMESPACE>
oc get job <JOB_NAME> -n <NAMESPACE> -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

> **⚠️ Uncertain (kept as recorded):** one recorded bridge-job image lookup — `oc get job loki-s3-bridge -n openshift-gitops -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'` — queries the job in `openshift-gitops`, while the same job is queried against `openshift-logging` everywhere else in the source. Possibly a copy-paste namespace mismatch; use `-n <NAMESPACE>` and confirm which namespace the job actually lives in before trusting the result.

---

## Reaching Internal Endpoints

**Cluster-internal services are not reachable from your laptop. Curl them from a pod that already has network and identity.**

```bash
# Borrow the consumer's token
TOKEN=$(oc get secret <SECRET_NAME> -n <NAMESPACE> -o jsonpath='{.data.token}' | base64 -d)

# Query Loki per tenant — <TENANT> is application | infrastructure | audit
oc exec -n <NAMESPACE> deploy/<DEPLOYMENT> -c <CONTAINER> -- curl -sS -k \
  -H "AUTHORIZATION: Bearer $TOKEN" \
  https://<LOKI_GATEWAY>.<LOKI_NS>.svc:8080/api/logs/v1/<TENANT>/loki/api/v1/labels

# Prometheus health
oc exec -n <NAMESPACE> deploy/<DEPLOYMENT> -c <CONTAINER> -- curl -sk \
  https://<PROMETHEUS_SVC>.<PROMETHEUS_NS>.svc.cluster.local:9090/-/healthy
```

> **⚠️ Uncertain (kept as recorded):** `oc exec -n <GRAFANA_NAMESPACE> deploy/<GRAFANA_DEPLOYMENT> -c grafana -- curl -sk -H https://<PROMETHEUS_SVC>:9090/~/healthy` — `-H` expects a header value, not a URL, and no separate target URL is passed to `curl`. As written this looks incomplete or malformed rather than a working health check. Use the clean form above (`curl -sk https://<PROMETHEUS_SVC>...:9090/-/healthy`, no `-H`) instead; this variant is preserved because it's what was actually run.

---

## Generic Inspection

Patterns that apply to any custom resource with a `.status`/`.status.conditions` block, not just Argo or Loki types.

```bash
oc get <KIND> -n <NAMESPACE>
oc get <KIND> -n <NAMESPACE> -o name
oc get namespace <NAMESPACE>
oc get <KIND> <NAME> -n <NAMESPACE>
oc get <KIND> <NAME> -n <NAMESPACE> -o jsonpath='{range .status.conditions[*]}{.type}:{.message}{"\n"}{end}'
oc get pod -l <LABEL_SELECTOR> -n <NAMESPACE> -o jsonpath='{range .status.conditions[*]}{.type}:{.message}{"\n"}{end}'
oc get <KIND> <NAME> -n <NAMESPACE> -o jsonpath='sync={.status.sync.status} health={.status.health.status}'
oc get <KIND> <NAME> -n <NAMESPACE> -o jsonpath='{range .status.resources[?(@.kind=="<KIND>")]}{.name}: {.status} {.health.status}{"\n"}{end}'
```

---

## Key Patterns

| Symptom | Move |
|---|---|
| Namespace stuck `Terminating` | Loop-patch `finalizers:null` over all Argo resources in it |
| Sync ignored, no new operation | `operation:null` first, then hard refresh, then force sync |
| `ConstraintsNotSatisfiable` | Package is not in any subscribed catalog — grep `packagemanifest` for the real name |
| Argo reports `forbidden` | `can-i --as=` the application controller against the target namespace |
| App healthy, one child broken | Filter `.status.resources[?(@.kind=="...")]` |
| S3 / Loki TLS refused | Extract cert + service CA, `openssl verify` the chain |
| Field reverts after apply | `--server-side --force-conflicts --field-manager=` |
| Short name resolves to nothing / wrong thing | Qualify by full API group, especially on `patch`/`can-i` |
