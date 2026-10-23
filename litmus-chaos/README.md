# litmus-chaos (app-pod-kill)

Weekly chaos job on **Litmus**: scan **all namespaces**, and for each **Deployment / StatefulSet / DaemonSet** with **`spec.replicas` ≥ 2** (DaemonSet: desired nodes ≥ 2), kill **one** pod that has been Running ≥ 10 minutes.

If the controller is defined as **1 replica** → **SKIP**, even if two pods are Running during a rollout.

Works on any cluster (GKE / EKS / AKS / k3s).

Uses a **unique ServiceAccount** `litmus-app-pod-kill` in namespace `litmus`. Never `default`.

This is the Litmus equivalent of the old Chaos Mesh **Schedule → Workflow Task → PodChaos**. Not a Kubernetes CronJob.

**UI limitation:** ChaosCenter **does not** list this schedule. Experiments in the portal are only those created in the UI / litmusctl. This CronWorkflow is GitOps (`Argo CD` Application `litmus-app-pod-kill`). It **runs on the cluster**; Chaos Experiments stays empty. Uploading `schedule-kill-pods.yaml` in the UI fails (`errorInYamlDescription`). Check runs with `kubectl` / Argo Workflows, not Chaos Studio.

---

## Who does what?

One pipeline, not two jobs fighting. Each kill creates **both** a ChaosEngine and a Litmus Job.

| Piece | Role (Chaos Mesh equivalent) |
|--------|------------------------------|
| **CronWorkflow `app-pod-kill`** | **Schedule.** Friday 09:00. One alpine Workflow pod. |
| **Workflow step `kill-one`** | **Task.** Alpine picks KILL vs SKIP. It does **not** delete app pods. |
| **ChaosExperiment `pod-delete`** | **Catalog / recipe.** Image, command, RBAC for the experiment Job. ChaosEngine only *names* this. |
| **ChaosEngine (`kill-…`)** | **PodChaos.** One CR per killed pod (`TARGET_PODS`). |
| **Job (`pod-delete-…`)** | Created by chaos-operator from the ChaosExperiment. This Job actually deletes the app pod. |
| **SA `litmus-app-pod-kill`** | Unique identity (not `default`). |
| **Litmus kubernetes-agent** | workflow-controller runs the CronWorkflow; chaos-operator runs each ChaosEngine. |

```text
Friday 09:00 Asia/Jerusalem
    → CronWorkflow app-pod-kill  (one alpine pod)
    → kill-one: desired ≥ 2 + age ≥ 10m → apply ChaosEngine kill-<pod>-…
    → chaos-operator reads ChaosExperiment pod-delete
    → creates Job pod-delete-…  → deletes that app pod
    → after Succeeded: Job/engine/experiment-pods are deleted (see Cleanup)
```

---

## What `kill-one` does (the script)

Image: `alpine/k8s:1.32.13` (`kubectl` + `sh` + `awk`).

### 1. Cleanup (so Jobs/pods do not pile up)

At start **and** after this run’s engines complete:

- ChaosEngine / ChaosResult with label `app.kubernetes.io/name=app-pod-kill`
- Jobs and pods `name=pod-delete` (the Litmus experiment Jobs)

`jobCleanUpPolicy: delete` — Litmus must not `retain` experiment Jobs.  
CronWorkflow `successfulJobsHistoryLimit: 0` + `ttlStrategy` — the alpine Workflow pod is removed too, so Argo CD does not keep Failed/Succeeded extras.

### 2. Load controllers (HA source of truth)

Not “how many pods are Running right now”:

| Kind | Field used as `desired` |
|------|-------------------------|
| Deployment | `spec.replicas` |
| StatefulSet | `spec.replicas` |
| DaemonSet | `status.desiredNumberScheduled` (nodes) |
| ReplicaSet | climb to parent **Deployment**; if none, `ReplicaSet.spec.replicas` |
| Job / other | SKIP (`owner=… not a scale controller`) |

Empty / non-numeric `replicas` is treated as **1** → SKIP.

### 3. List Running pods, group by **controller**

Example: pods owned by ReplicaSet `backend-abc` belong to Deployment `backend`. All of them are one group.

### 4. Decide

| Condition | Result |
|-----------|--------|
| `desired < 2` | **SKIP** |
| `desired ≥ 2` but fewer than 2 Running | **SKIP** |
| `desired ≥ 2`, ≥ 2 Running, pod age ≥ 10 min | **KILL one** (create ChaosEngine), then next group |
| All candidates younger than 10 min | **SKIP** |

```text
KILL secretpass/backend-… (desired=3 running=3 age=…s Deployment/backend)
SKIP argocd/prod-argocd-redis-… (desired=1 running=2 Deployment/prod-argocd-redis)
```

### 5. How the kill happens (not `kubectl delete`, not CronJob)

Alpine applies a **ChaosEngine** in namespace **`litmus`**:

- experiment name `pod-delete` (must exist as ChaosExperiment — see Files)
- `TARGET_PODS` = that exact pod name
- `selectors.pods` = namespace + name
- annotation `app-pod-kill/target: ns/pod`
- `jobCleanUpPolicy: delete`

Then chaos-operator creates the `pod-delete-*` Job, which deletes the app pod. ReplicaSet/Deployment creates a replacement.

That is why one Friday run shows many `kill-*` **and** many `pod-delete-*`: one ChaosEngine + one Job **per HA controller**, not a double script.

---

## Where to look (not ChaosCenter Experiments)

| What you want | Where |
|---------------|--------|
| Schedule | `kubectl get cronworkflow -n litmus app-pod-kill` / Argo CD `litmus-app-pod-kill` |
| This run’s alpine pod | `kubectl get workflow -n litmus` (gone after TTL) |
| Targets | ChaosEngine annotation, while the run is in progress |

Filter namespace **litmus** (engines live here), not the app namespace.

```bash
kubectl get chaosengine -n litmus -l app.kubernetes.io/name=app-pod-kill \
  -o custom-columns='NAME:.metadata.name,TARGET:.metadata.annotations.app-pod-kill/target'
```

---

## Files

| File | Kind | Why it exists |
|------|------|----------------|
| `replica-check-rbac.yaml` | SA + ClusterRole | Unique SA; alpine and the experiment Job are not `default` |
| `schedule-kill-pods.yaml` | CronWorkflow | **When** and **which** pod. Applies ChaosEngine. Does not contain the kill recipe. |
| `pod-delete-experiment.yaml` | ChaosExperiment `pod-delete` | **How** to kill. ChaosEngine only references `name: pod-delete`. The agent Helm chart does **not** install this catalog; without this CR the engine has nothing to run. Do not delete it. |
| `application.yml` | Argo CD Application | Syncs this folder to namespace `litmus` (`litmus-app-pod-kill`) |

**Prerequisite:** Litmus ChaosCenter **and** kubernetes-agent (workflow-controller + chaos-operator) in namespace `litmus`. Same idea as “Chaos Mesh chart already installed”. Without the agent, CronWorkflow / ChaosEngine CRs have no controller and the UI has no runs.

Agent install (same cluster as ChaosCenter): [Litmus agent Helm](https://docs.litmuschaos.io/docs/user-guides/litmus-agent-helm-installation). Needs Project ID + Environment ID from the portal.

---

## Schedule

```text
0 9 * * 5
```

- **When:** every **Friday at 09:00**
- **Timezone:** `Asia/Jerusalem` (`CronWorkflow.spec.timezone`)
- `concurrencyPolicy: Allow`
- `successfulJobsHistoryLimit: 0` / `failedJobsHistoryLimit: 0` + `ttlStrategy` — do not keep finished Workflow pods (Argo CD will not sit on Failed leftovers)

---

## Why unique SA + extra RBAC?

Chaos Mesh Task pods used SA **`default`**. This job does **not**.

Alpine **does not** `kubectl delete` application pods. It only creates **ChaosEngine**. The operator/experiment uses **`litmus-app-pod-kill`** to perform pod-delete.

| API group | Resources | Verbs | Why |
|-----------|-----------|-------|-----|
| `""` (core) | pods, pods/log, events | get, list, delete, create, patch | List Running; experiment deletes the chosen pod |
| `apps` | deploy, rs, sts, ds | **get, list only** | Read **desired** replicas |
| **`litmuschaos.io`** | chaosengines, chaosexperiments, chaosresults | get, list, **create, update, patch, delete** | UI cards |
| `batch` | jobs | get, list, create, update, patch, delete | Operator experiment Job |

---

## Deploy / sync

Argo CD Application: `litmus-app-pod-kill` (`application.yml`).

```bash
kubectl apply -f litmus-chaos/application.yml
```

---

## Useful commands

```bash
kubectl get cronworkflow -n litmus app-pod-kill
kubectl get workflow -n litmus
kubectl logs -n litmus -l app.kubernetes.io/name=app-pod-kill --tail=200

kubectl get chaosengine -n litmus -l app.kubernetes.io/name=app-pod-kill \
  -o custom-columns='NAME:.metadata.name,TARGET:.metadata.annotations.app-pod-kill/target'
```

---

## Short summary

| Piece | Role |
|--------|------|
| **CronWorkflow** | Friday trigger (Schedule) |
| **`kill-one` (alpine)** | Decides KILL vs SKIP from **desired replicas** |
| **ChaosExperiment `pod-delete`** | Recipe for the experiment Job (required) |
| **ChaosEngine + Job `pod-delete-*`** | Executes the kill, then both are deleted |
| **SA `litmus-app-pod-kill`** | Unique identity; not `default` |

Rule: **`spec.replicas` ≥ 2 (or DaemonSet on ≥ 2 nodes) and pod age ≥ 10m → kill one; `replicas: 1` → skip.**
