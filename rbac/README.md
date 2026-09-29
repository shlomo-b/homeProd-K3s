# Kubernetes identity for the external MCP server

Copy this `rbac/` folder to the K3s **master**. Apply **only after approval**.

This ServiceAccount is a Kubernetes identity, not a Pod. The MCP process runs on the Linux test server and authenticates with a dedicated kubeconfig.

```bash
kubectl apply -k .
```

Then generate the kubeconfig on the master with `../scripts/create-kubeconfig.sh` (needs cluster-admin there). Copy the resulting file to the test server as `/etc/mcp/kubeconfig`. Do not use `/etc/rancher/k3s/k3s.yaml` on the MCP host.
