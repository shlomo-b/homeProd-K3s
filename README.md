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

#### Initial Setup

The cluster is configured using the root application which deploys ArgoCD and initializes the App of Apps pattern for managing all other applications and resources.

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