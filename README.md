# HomeProd-K3s

A production-grade Kubernetes infrastructure setup for home lab environments using K3s, GitOps, and comprehensive monitoring.

![K3s Architecture](https://img.shields.io/badge/Architecture-K3s-brightgreen)
![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-blue)
![Monitoring](https://img.shields.io/badge/Observability-Prometheus%2C%20Grafana%2C%20Loki-orange)

## Overview

This project implements a production-ready Kubernetes environment using K3s (lightweight Kubernetes) with 1 master and 3 worker nodes. It leverages GitOps principles with ArgoCD for deployment and configuration management, and includes a comprehensive monitoring stack.
This is an actively maintained project that will continue to evolve with new features, improvements, and best practices over time.

## Architecture

- **K3s Cluster**: Lightweight Kubernetes with 1 master and 3 worker nodes
- **GitOps**: ArgoCD for declarative, Git-based application deployment
- **App of Apps Pattern**: Hierarchical application management
- **Monitoring**: Grafana, Loki, Promtail, and Uptime-Kuma
- **Certificate Management**: Let's Encrypt certificates with cert-manager
- **Domain Management**: AWS Route53 with external-dns for automatic DNS records creation
- **Authentication**: SSO integration with Azure AD
- **Secrets Management**: AWS Secrets Manager integration via external-secrets operator
- **Ingress**: Traefik as the ingress controller
- **Load Balancing**: MetalLB for bare metal load balancing with dedicated IP pools for different services

## Features

### ArgoCD Configuration

The GitOps workflow is managed through ArgoCD, which is structured using the App of Apps pattern:

- **Root Application**: Deploys and manages all other ArgoCD applications
- **Monitoring Project**: Dedicated ArgoCD project specifically for monitoring tools (Grafana, Loki, Promtail, and Uptime-Kuma)
- **Default Project**: Other applications (blackjack, shop-online, etc.) are deployed in the default project

This structure provides clear separation between monitoring resources and application resources, making it easier to manage and view related applications together.

### Network Configuration

The cluster uses MetalLB to provide load balancing capabilities on bare metal:

- **IP Address Pools**: Dedicated address pools for different service categories (monitoring, ArgoCD, general applications)
- **Service Type LoadBalancer**: Enables Kubernetes services to receive dedicated external IPs
- **Integration with Ingress**: Works with Traefik to provide external access to services

### Monitoring Stack

- **Grafana**: Metrics visualization and dashboards
- **Prometheus**: Metrics collection and time series database
- **Loki**: Log aggregation system
- **Promtail**: Log collection agent that ships logs to Loki
- **Uptime-Kuma**: Uptime monitoring and alerting

### Cluster-Wide Resources

The project uses a set of cluster-wide resources to provide core functionality across all applications:

- **ClusterIssuer**: Integrates with Let's Encrypt for automated certificate management through cert-manager
- **ClusterSecretStore**: Works with external-secrets operator to securely retrieve secrets from AWS Secrets Manager

These resources enable secure secret management and automated TLS certificate provisioning for all applications in the cluster without requiring application-specific configuration.

### CI/CD Integration

- **Docker Build Pipeline**: Automatic rebuilds when source code changes
- **Deployment Pipeline**: Automatic updates to application configuration
- **Keel**: Automatic deployments for container updates
- **Backup Pipeline**: Scheduled cronjobs for backing up network devices and infrastructure components

### Application Management

- **Blackjack Application**: Sample application with full CI/CD
- **Shop Online**: E-commerce application with TLS certificates
- **Certificate Management**: Automated certificate issuance and renewal with Let's Encrypt
- **DNS Management**: Automatic DNS record creation in AWS Route53 via external-dns monitoring Ingress resources
- **Scheduled Backups**: Cronjobs for automated backups of network devices and infrastructure

### Installation

#### Prerequisites

- K3s cluster with at least 1 master and 1 worker node (this project uses 1 master and 3 worker nodes)
- Sufficient system resources on nodes to run monitoring stack and applications
- kubectl configured to access your cluster
- Git repository for storing configuration
- AWS account for Route53 and AWS Secrets Manager
- Azure AD account (for SSO configuration)
- GitHub account with repository access
- kubectl and helm installed locally
- AWS CLI configured

## Getting Started
<details><summary>Click to infrastructure deployment and application deployment</summary>
### ArgoCD Installation

1. Add the ArgoCD Helm repository:
   ```bash
   helm repo add argo https://argoproj.github.io/argo-helm
   helm repo update
   ```

2. Install ArgoCD:
   ```bash
   helm install prod-argocd argo/argo-cd --namespace argocd --create-namespace --version 7.7.23
   ```
2.2 (Optional) For SSO integration and certificates, you can use a values file:
Create a values.yml file with your custom configuration
Then upgrade the chart with:
```bash
helm upgrade prod-argocd argo/argo-cd --namespace argocd --create-namespace --version 7.7.23 --values values.yml
```

3. Get the ArgoCD admin password:
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

4. Access the ArgoCD UI using port-forward:
   ```bash
   kubectl port-forward svc/prod-argocd-server -n argocd 8080:443
   ```
   Then visit: https://localhost:8080

5. Apply the repository configuration(update your repo url):
   ```bash
   kubectl apply -f repo.yml
   ```

### Application Deployment argocd and app of apps
1. Apply the MetalLB pool configuration:
   ```bash
   kubectl apply -f pool-alb/pool-alb-application.yml
   ```

2. Apply the root application(app of apps pattern):
   ```bash
   kubectl apply -f app-of-apps/root-application.yaml

   The app of apps includes the following applications: chart-cert-manager, chart-external-dns, chart-external-secrets, chart-grafana, chart-keel, chart-loki, chart-metallb, chart-prometheus, chart-promtail, chart-traefik, chart-uptime-kuma

    Note: If you don't need all applications, you can modify the root-application.yml file to remove or disable specific applications before applying.
   ```
</details>

### Maintenance

#### Adding New Applications

1. Create application directory in `k8s-apps/`
2. Define application resources
3. Add application to the root application

#### Certificate Renewal

Certificates are automatically renewed by cert-manager before expiration.

#### Monitoring Updates

Monitoring tools are deployed and updated as Helm charts. To update:

1. Update the relevant chart version in your configuration
2. Commit changes to Git
3. ArgoCD will automatically sync the changes