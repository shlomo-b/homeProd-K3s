# Litmus ChaosCenter + Agent (Argo CD)

**UI limitation:** ChaosCenter lists only experiments created in the portal (or litmusctl). The weekly kill is an Argo `CronWorkflow` in `litmus-chaos/schedule-kill-pods.yaml` — it **runs on the cluster** (workflow-controller + chaos-operator) but **does not appear** under Chaos Experiments. Uploading that YAML in the UI fails (`errorInYamlDescription`); it is not a Litmus experiment spec. Infrastructure **Active** is not a run history.

**Litmus** is chaos engineering for Kubernetes: it registers a cluster as Infrastructure and runs experiments (pod-delete, workflows, schedules) against workloads.

ChaosCenter (control plane) is three pods plus Mongo:

| Component | What it does |
|-----------|----------------|
| **frontend** | Web UI (login, Environments, Enable Chaos, experiments). |
| **auth-server** | Authentication and users (admin login, tokens). |
| **server** (GraphQL) | API: register Infrastructure, Confirm, issue `INFRA_ID` / `ACCESS_KEY`. |

**Agent** is the execution engine on the cluster: it is what **runs the workflows**. ChaosCenter is only the portal (UI + API + keys). It does not start a `CronWorkflow` or delete pods. Without the agent, Enable Chaos / Active in the UI does nothing on the cluster.

The agent chart (`litmus-agent`) registers as Infrastructure (`INFRA_ID` + `ACCESS_KEY`). After that, **workflow-controller** runs the schedule (`CronWorkflow`), and **chaos-operator** runs each `ChaosEngine` (pod-delete).

| Component | What it does |
|-----------|----------------|
| **subscriber** | Connects to ChaosCenter (websocket). Confirm, health, Infrastructure **Active**. |
| **workflow-controller** | Argo controller. Runs `CronWorkflow` / `Workflow` (the scheduled kill job). This is why the agent is required for the weekly schedule. |
| **chaos-operator** | Watches `ChaosEngine` and runs the fault (pod-delete). |
| **chaos-exporter** | Optional Prometheus metrics. Disabled here. |
| **event-tracker** | Optional ChaosCenter GitOps events. Disabled here. |

Argo Application: `litmus-chaos` (`litmus-application.yaml`).  
Two Helm charts in namespace `litmus`, version **3.30.0**:

| Chart | Values | Role |
|--------|--------|------|
| `litmus` | `values-litmus-frontend.yaml` | ChaosCenter (frontend, server, auth) |
| `litmus-agent` | `values-litmus-agent.yaml` | Agent (subscriber, chaos-operator, workflow-controller) |

Two issues were fixed: **MongoDB**, then **agent registration with Argo CD**.

---

## 1. MongoDB — what broke and how it was fixed

The Litmus chart ships **Bitnami** MongoDB. This cluster uses **official** Mongo (`mongo:9.0.2`, replica set + `keyFile` + `MONGO_INITDB_*`), outside the subchart.

In `values-litmus-frontend.yaml`:

```yaml
mongodb:
  enabled: false   # not Bitnami

adminConfig:
  DB_SERVER: "mongodb://mongodb:27017"
```

**Bug:** `DB_SERVER: mongodb://litmus:27017` is parsed as username=`litmus` and host=`27017`. The `wait-for-mongodb` Job never connects.

**Fix:** the host is the Service name **`mongodb`**, not the namespace `litmus`.  
A replica set also needs a `keyFile`. Without it, auth + replica set fails.

---

## 2. Agent — why the Job breaks with Argo CD

The `litmus-agent` chart runs a **pre-install Job** that logs into ChaosCenter (username/password), registers the Infrastructure, and fills:

- Secret `subscriber-secret` → `INFRA_ID`, `ACCESS_KEY`
- ConfigMap `subscriber-config` → `SERVER_ADDR`, `VERSION`, `IS_INFRA_CONFIRMED`, …

Helm `pre-install` hooks run on **every Argo sync**, not only the first install. Argo creates **empty** Secret/ConfigMaps (hooks + ServerSideApply). The Job fills them; Argo then overwrites. Pods crash with missing `ACCESS_KEY` or `accessID MISMATCH`.

After the Subscriber **Confirm**, ChaosCenter **rotates** `ACCESS_KEY` (32 chars → ~44 char Base64). A JWT from the UI / GraphQL is **not** `ACCESS_KEY`.

So the Job is disabled and keys come from AWS/GCP/Azure via External Secrets:

```yaml
# values-litmus-agent.yaml
enablePreInstallJob: false
useExistingInfraSecret: true
useExistingInfraConfigMap: true
useExistingWorkflowControllerConfigMap: true
useExistingHookSecret: true

global:
  infraSecretName: subscriber-secret
  infraConfigName: subscriber-config
```

ESO (not Litmus) creates `subscriber-secret`.  
ConfigMaps are **not** created by ESO. They must exist in the cluster (`subscriber-config` with `IS_INFRA_CONFIRMED: "true"`, and `workflow-controller-configmap` with `instanceID` equal to the same `INFRA_ID`).

---

## 3. Two ways to supply `INFRA_ID` + `ACCESS_KEY`

These are the **only two** bootstrap paths. They differ in **who registers** the Infrastructure. After that they are identical: AWS holds the keys, ESO owns the cluster Secret, the Job stays off.

| | Option 1 | Option 2 (what this cluster uses) |
|--|----------|-----------------------------------|
| Job | `true` once, then `false` | `false` from the start |
| Who registers | Helm pre-install Job | ChaosCenter UI (**Enable Chaos**) |
| Keys first appear in | Kubernetes `subscriber-secret` (Job wrote it) | UI card + deploy YAML |
| Then | Copy that Secret into AWS | Put the UI pair into AWS |
| Who creates `subscriber-secret` after that | ESO | ESO |
| ConfigMaps | Job created them; leave them | Create them yourself (Job never ran) |

**Where things are written (do not mix these):**

| What | Where | Not here |
|------|--------|----------|
| `INFRA_ID` + `ACCESS_KEY` | AWS Secrets Manager secret named **`litmus-subscriber`** (JSON) | **Never** `values-litmus-agent.yaml` |
| ExternalSecret wiring | `applications/platform-infra/secrets-management/values.yaml` block `litmus-subscriber` | Agent values |
| Job on/off | `app-of-apps/chart-litmus/values-litmus-agent.yaml` → `enablePreInstallJob` | AWS |
| `useExisting*: true` | same agent values file, after bootstrap | — |

Names:

| Where | Name |
|--------|------|
| AWS Secrets Manager | `litmus-subscriber` |
| ExternalSecret | `litmus-subscriber` (namespace `litmus`) |
| Kubernetes Secret (target) | `subscriber-secret` |
| ClusterSecretStore | `aws-secret-store` |

Block already in `applications/platform-infra/secrets-management/values.yaml`:

```yaml
litmus-subscriber:
    external_secret_name: litmus-subscriber
    namespaces:
      - litmus
    refreshInterval: 0s
    secretStoreRefName: aws-secret-store
    target: subscriber-secret
    dataFrom:
      extract:
        key: litmus-subscriber
```

`dataFrom.extract` copies JSON keys as-is into `subscriber-secret`.

AWS JSON (do not commit real values):

```json
{
  "ACCESS_KEY": "<post-confirm-access-key>",
  "INFRA_ID": "<uuid-from-chaoscenter>"
}
```

- `INFRA_ID` — Infrastructure UUID in ChaosCenter.
- `ACCESS_KEY` — after Confirm ~44 Base64 chars; before Confirm ~32 chars. **Not a JWT.**

`refreshInterval: 0s` = no periodic refresh. AWS must hold the **final key after Confirm**. If AWS still has the old key, ESO can write it back over the Secret.

---

### Option 1 — Job creates the Secret → copy to AWS via ESO → Job `false`

Use this when you want Litmus to register itself.

1. In `values-litmus-agent.yaml` set `enablePreInstallJob: true` (and allow the chart/Job to create the Secret and ConfigMaps — `useExisting*` not blocking creation).
2. Sync / install the agent. The Job logs into ChaosCenter (`LITMUS_USERNAME` / `LITMUS_PASSWORD`), registers the Infrastructure, and writes:
   - Secret `subscriber-secret` (`INFRA_ID`, `ACCESS_KEY`)
   - ConfigMap `subscriber-config`
   - ConfigMap `workflow-controller-configmap` (`instanceID` = that `INFRA_ID`)
3. Wait until Confirm finishes: UI **Active**, `ACCESS_KEY` ~44 chars (rotated). Copy **that** pair, not the pre-Confirm key:

```bash
kubectl get secret subscriber-secret -n litmus -o jsonpath='{.data.INFRA_ID}' | base64 -d; echo
kubectl get secret subscriber-secret -n litmus -o jsonpath='{.data.ACCESS_KEY}' | base64 -d; echo
```

4. Put that JSON in AWS Secrets Manager as **`litmus-subscriber`**. The ExternalSecret block in `secrets-management/values.yaml` is already there; sync `secrets-management` so ESO owns `subscriber-secret`.
5. In `values-litmus-agent.yaml` set `enablePreInstallJob: false` and all `useExisting*: true`. Sync `litmus-chaos`. The Job never runs again.

If `subscriber-secret` is deleted later, ESO recreates it from AWS. **Do not delete** the two ConfigMaps.

**Argo CD:** a later sync with the Job still `true` can recreate **empty** hook Secret/CMs and wipe what the Job just wrote. Copy to AWS and set the Job `false` before that next sync. If Argo already emptied the Secret, Option 1 is done — use Option 2.

---

### Option 2 — Job `false` from the start → Enable Chaos in the UI → keys in AWS

Use this when you skip the Job entirely (this cluster). The UI registers the Infrastructure. Git already has `enablePreInstallJob: false` and `useExisting*: true`.

**“Update values” means only the two Git files above** (Job flag + ExternalSecret wiring). It does **not** mean pasting `INFRA_ID` / `ACCESS_KEY` into `values-litmus-agent.yaml`. Those two strings go only in AWS.

1. ChaosCenter → **Environments** → **`prodlitmus`** (`LITMUS_ENVIRONMENT_ID`). Not a different environment.
2. **Enable Chaos** (or **+ Enable Chaos**).
3. Overview: name (same idea as `INFRA_NAME`). Configure: Cluster, namespace `litmus`, Service Account.
4. After save the card is **PENDING**. Next to **id:** copy the UUID — that is **`INFRA_ID`**.
5. **Deploy the setup**: in the YAML / connect command copy:

```yaml
INFRA_ID: "...."
ACCESS_KEY: "...."
```

That is the **initial** key (~32 chars). Do not copy a token/JWT. Do **not** `kubectl apply` the full UI manifest — Argo already installs the agent.

6. Put that pair in AWS `litmus-subscriber`. Sync `secrets-management`. ESO creates `subscriber-secret`.
7. Because the Job never ran, create/keep the ConfigMaps yourself:
   - `subscriber-config` — start with `IS_INFRA_CONFIRMED: "false"`
   - `workflow-controller-configmap` — `instanceID` equal to this `INFRA_ID`
8. Sync `litmus-chaos`. Subscriber starts → Confirm → UI **Active** and `ACCESS_KEY` **rotates**.
9. **Required:** update AWS with the **final** `ACCESS_KEY` (~44 chars):

```bash
kubectl get secret subscriber-secret -n litmus -o jsonpath='{.data.ACCESS_KEY}' | base64 -d; echo
```

Then set `IS_INFRA_CONFIRMED: "true"` on `subscriber-config`.

Without step 9, ESO can restore the pre-Confirm key → `accessID MISMATCH`.  
`INFRA_ID` and `ACCESS_KEY` must be from the **same** Infrastructure. Do not mix a new UI id with an old key.

---

## Bring-up order

1. AWS `litmus-subscriber` is filled (post-Confirm).
2. ConfigMaps `subscriber-config` and `workflow-controller-configmap` exist.
3. Argo syncs secrets-management, then litmus-chaos.
4. `kubectl get pods -n litmus` — subscriber / operator / workflow-controller are `Running`.
5. UI: Infrastructure **Active**.

---

## Other notes (not extra incidents)

These were configuration gotchas, not a third outage:

- Same-cluster URLs must use the real Service names: `litmus-chaos-frontend-service` and `litmus-chaos-server-service` (not `litmusportal-*`).
- `LITMUS_BACKEND_URL` has no `/query`; ConfigMap `SERVER_ADDR` **does** include `/query`.
- ChaosCenter and agent `APP_VERSION` must match (`3.30.0`).
- `PLATFORM_NAME: "Others"` (`k3s` is not an official value).
- Do not turn `enablePreInstallJob` back on while ESO owns `subscriber-secret` — the Job and ESO will fight.
- `creationPolicy: Orphan` in values is ignored; the secrets-management template hardcodes `Owner`.
- `LITMUS_USERNAME` / `LITMUS_PASSWORD` in agent values are only for the Job. With the Job off they are unused; do not treat them as `ACCESS_KEY`.
- Option 2 must use environment `prodlitmus` (`LITMUS_ENVIRONMENT_ID`), not a different Environment in the UI.
