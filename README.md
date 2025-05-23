# HomeProd-K3s

A home lab Kubernetes environment implementing production-grade infrastructure practices with K3s, GitOps, and comprehensive monitoring.

![K3s Architecture](https://img.shields.io/badge/Architecture-K3s-brightgreen)
![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-blue)
![Monitoring](https://img.shields.io/badge/Observability-Prometheus%2C%20Grafana%2C%20Loki-orange)

## Overview

This project implements a home lab Kubernetes environment using K3s (lightweight Kubernetes) with 1 master and 3 worker nodes. It leverages GitOps principles with ArgoCD for deployment and configuration management, and includes a comprehensive monitoring stack.
This is an actively maintained project that will continue to evolve with new features, improvements, and best practices over time.

## Architecture

- **K3s Cluster**: Lightweight Kubernetes with 1 master and 3 worker nodes
- **GitOps**: ArgoCD for declarative, Git-based application deployment
- **App of Apps Pattern**: Hierarchical application management
- **Monitoring**: Grafana,Prometheus, Loki, Promtail, and Uptime-Kuma
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
- **Monitoring Project**: Dedicated ArgoCD project specifically for monitoring tools (Grafana,Prometheus, Loki, Promtail, and Uptime-Kuma)
- **AppServices**: Dedicated ArgoCD project specifically for application services
- **Default Project**: Other applications are deployed in the default project

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
<details><summary>Click to expand deployment instructions</summary>


### Infrastructure Deployment

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
    Create a values.yaml file with your custom configuration
    Then upgrade the chart with:
    ```bash
    helm upgrade prod-argocd argo/argo-cd --namespace argocd --create-namespace --version 7.7.23 --values values.yaml
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
### Application Deployment app of apps
1. Apply the root application(app of apps pattern):
   ```bash
   kubectl apply -f app-of-apps/root-application.yaml

   The app of apps includes the following applications: chart-cert-manager, chart-external-dns, chart-external-secrets, chart-grafana, chart-keel, chart-loki, chart-metallb, chart-prometheus, chart-promtail, chart-traefik, chart-uptime-kuma
   
### Application Deployment pool-alb for MetalLB
1. Apply the MetalLB pool configuration:
   ```bash
   kubectl apply -f pool-alb/pool-alb-application.yml
   ```

    Note: If you don't need all applications, you can modify the root-application.yml file to remove or disable specific applications before applying.

### Application Deployment cluster wide resources
   ClusterIssuer and ClusterSecretStore are required if you want to use cert-manager and external-secrets:

1. Apply the ClusterIssuer and ClusterSecretStore configuration with argocd:
   ```bash
   kubectl apply -f k8s-apps/cluster-wide-resources/Cluster-wide-application.yml
   ---

   These resources enable secure secret management and automated TLS certificate provisioning for all applications in the cluster without requiring application-specific configuration.
   AWS Credentials Requirements:

   For cert-manager: Create an IAM user with permissions to modify Route53 records for DNS validation. The access key and secret key must be stored as a Kubernetes secret referenced by the ClusterIssuer, or use a service account.

   For external-secrets: Create an IAM user with permissions to read from AWS SecretsManager. The access key and secret key must be stored as a Kubernetes secret referenced by the ClusterSecretStore, or use a service account.

   Note: Examples of how to use certificates and external secrets in your applications can be found in the folder manage-certificates-apps and manage-secrets-apps:

Certificate examples: see k8s-apps/manage-certificates-apps/
External secrets examples: see k8s-apps/blackjack and k8s-apps/shop-online

### Backup Configuration optional
   Deploy the cronjob for backing up network devices:

1. Apply the cronjob configuration:
   ```bash
   kubectl apply -f cronjob-application.yml
   ---
   The cronjob requires the following secret keys:

   BUCKET_NAME - AWS S3 bucket name for storing backups
   HOST - Hostname or IP address of the device to back up
   PORT - SSH port for connecting to the device
   USERNAME - SSH username for authentication
   PASSWORD - SSH password for authentication
   AWS_ACCESS_KEY_ID - AWS credentials for S3 access
   AWS_SECRET_ACCESS_KEY - AWS credentials for S3 access

   These secrets are transferred from external-secrets, which retrieves them from AWS Secrets Manager, provid

### Application Deployment options (shop-online and blackjack)
   Before deploying, please note:

   Both applications can be deployed with or without TLS certificates
   Blackjack application is a simple standalone app that doesn't require additional configuration but optionally can use ingress with TLS
   Shop-online requires both ConfigMaps and secrets from external-secrets


1. Apply the shop-online and blackjack applications:
   ```bash
   kubectl apply -f k8s-apps/shop-online/root-application.yml
   kubectl apply -f k8s-apps/blackjack/root-application.yml

   Note:

   To use these applications, you need to deploy the root application in ArgoCD
   The shop-online application requires the following environment variables to be transferred:

   Backend to Database connection:

   MONGO_DB_HOST - From ConfigMap
   MONGO_INITDB_ROOT_USERNAME - From external-secrets
   MONGO_INITDB_ROOT_PASSWORD - From external-secrets


   Frontend to Backend connection:

   REACT_APP_API_URL - From ConfigMap

   These applications demonstrate how to use external-secrets for secure credential management and cert-manager for TLS certificates with your ingress resources.

</details>

#### Adding New Applications

1. Create application directory in `k8s-apps/`
2. Define application resources
3. Add application to the root application

#### Certificate Renewal

Certificates are automatically renewed by cert-manager before expiration.

#### Monitoring Updates

Monitoring tools are deployed and updated as Helm charts. To update:

1. Update the relevant chart version in your configuration.
2. Commit changes to Git.
3. ArgoCD will automatically sync the changes.