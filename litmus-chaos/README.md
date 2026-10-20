# litmus-chaos (app-pod-kill)

Weekly chaos job on **Litmus**: scan **all namespaces**, and for each **Deployment / StatefulSet / DaemonSet** with **`spec.replicas` ≥ 2** (DaemonSet: desired nodes ≥ 2), kill **one** pod that has been Running ≥ 10 minutes.

If the controller is defined as **1 replica** → **SKIP**, even if two pods are Running during a rollout.

Works on any cluster (GKE / EKS / AKS / k3s).

Uses a **unique ServiceAccount** `litmus-app-pod-kill` in namespace `litmus`. Never `default`.

This is the Litmus equivalent of the old Chaos Mesh **Schedule → Workflow Task → PodChaos**. Not a Kubernetes CronJob.

---

## Who does what?

| Piece | Role (Chaos Mesh equivalent) |
|--------|------------------------------|
| **CronWorkflow `app-pod-kill`** | **Schedule.** Friday 09:00. Visible as a scheduled experiment. |
| **Workflow step `kill-one`** | **Task.** Alpine picks KILL vs SKIP. |
| **ChaosEngine (pod-delete)** | **PodChaos / Experiments.** One CR per killed pod. ChaosCenter shows the target. |
| **SA `litmus-app-pod-kill`** | Unique identity (not `default`). |
| **Litmus kubernetes-agent** | **Chaos Mesh chart.** Workflow controller + chaos-operator actually run the schedule and the kill. |

```text
Friday 09:00 Asia/Jerusalem
    → CronWorkflow app-pod-kill
    → Workflow step kill-one (alpine, SA litmus-app-pod-kill)
    → desired ≥ 2 + age ≥ 10m → apply ChaosEngine (pod-delete, TARGET_PODS=that pod)
    → chaos-operator runs pod-delete
    → ChaosCenter: schedule + workflow steps + experiment / ChaosEngine list
```

---

## What `kill-one` does (the script)

Image: `alpine/k8s:1.32.13` (`kubectl` + `sh` + `awk`).

### 1. Cleanup

Delete last week’s ChaosEngine with label `app.kubernetes.io/name=app-pod-kill` (same idea as `historyLimit: 1`).

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

- experiment `pod-delete`
- `TARGET_PODS` = that exact pod name
- `appinfo.appns` = that namespace
- annotation `app-pod-kill/target: ns/pod`

Then Litmus chaos-operator deletes the pod. ReplicaSet/Deployment creates a replacement.

---

## Where to look in the UI

| Chaos Mesh screen | Litmus equivalent |
|-------------------|-------------------|
| **Schedules** | CronWorkflow / Chaos Experiment schedule |
| **Workflows** | Workflow run (step `kill-one`) |
| **Experiments** | ChaosEngine list (one per kill) |

Filter namespace **litmus** (where engines are stored), not the app namespace.

```bash
kubectl get chaosengine -n litmus -l app.kubernetes.io/name=app-pod-kill \
  -o custom-columns='NAME:.metadata.name,TARGET:.metadata.annotations.app-pod-kill/target'
```

---

## Files

| File | Purpose |
|------|---------|
| `replica-check-rbac.yaml` | SA `litmus-app-pod-kill` + ClusterRole + binding |
| `schedule-kill-pods.yaml` | **CronWorkflow** (Schedule) → step `kill-one` + ChaosEngine create |
| `pod-delete-experiment.yaml` | Litmus `ChaosExperiment` `pod-delete` |
| `application.yml` | Argo CD Application (`./litmus-chaos`) |

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
- `successfulJobsHistoryLimit: 1` — keep one Workflow; script also deletes last week’s ChaosEngines

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
| **ChaosEngine pod-delete** | Executes the kill; UI card per target |
| **SA `litmus-app-pod-kill`** | Unique identity; not `default` |

Rule: **`spec.replicas` ≥ 2 (or DaemonSet on ≥ 2 nodes) and pod age ≥ 10m → kill one; `replicas: 1` → skip.**
