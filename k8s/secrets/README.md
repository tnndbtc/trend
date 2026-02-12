# Kubernetes Secrets Management

Three production-ready approaches for managing secrets in Kubernetes, all following the same principle: **secrets come from environment variables, never hardcoded in files**.

---

## 🎯 Quick Comparison

| Approach | Best For | Complexity | GitOps | Cloud Agnostic |
|----------|----------|------------|--------|----------------|
| **[Script from env](#1-script-from-environment-variables)** | Development, Quick start | ⭐ Low | ❌ No | ✅ Yes |
| **[Sealed Secrets](#2-sealed-secrets)** | GitOps workflows | ⭐⭐ Medium | ✅ Yes | ✅ Yes |
| **[External Secrets](#3-external-secrets-operator)** | Production, Enterprise | ⭐⭐⭐ High | ✅ Yes | ⚠️ Depends |

---

## 1. Script from Environment Variables

**📁 Directory**: `./create-from-env.sh`

### When to Use
- ✅ Development and testing
- ✅ Quick start scenarios
- ✅ Small teams without complex secret management needs
- ✅ When you want cloud-agnostic setup

### How It Works
```bash
# Set environment variables
export OPENAI_API_KEY='sk-proj-xxxxx'
export POSTGRES_PASSWORD='secure-password'

# Run script
./create-from-env.sh

# Script creates k8s secrets directly
```

### Pros
- ✅ Simple and straightforward
- ✅ No additional tools required (just kubectl)
- ✅ Works on any Kubernetes cluster
- ✅ Follows 12-factor app pattern

### Cons
- ❌ Secrets not tracked in git
- ❌ Manual process (not declarative)
- ❌ Need to re-run script on every cluster

### Security
- 🔐 Secrets stored only in k8s etcd (encrypted at rest)
- 🔐 Environment variables never committed to git
- 🔐 Script is safe to commit (reads from env vars)

---

## 2. Sealed Secrets

**📁 Directory**: `./sealed-secrets/`

### When to Use
- ✅ GitOps workflows (ArgoCD, Flux)
- ✅ Want secrets in version control (encrypted)
- ✅ Don't want dependency on cloud providers
- ✅ Need audit trail of secret changes

### How It Works
```bash
# 1. Set environment variables
export OPENAI_API_KEY='sk-proj-xxxxx'

# 2. Create and encrypt secret
./sealed-secrets/create-sealed-secrets.sh

# 3. Commit encrypted secret (safe!)
git add api-keys-sealed.yaml
git commit -m "Add API keys"
git push

# 4. Apply to cluster
kubectl apply -f api-keys-sealed.yaml

# Controller automatically decrypts and creates k8s secret
```

### Pros
- ✅ GitOps friendly (encrypted secrets in git)
- ✅ Declarative (managed as code)
- ✅ Cloud agnostic
- ✅ Audit trail in git history
- ✅ Secrets encrypted with cluster-specific key

### Cons
- ❌ Requires controller installation
- ❌ Secrets tied to specific cluster (can't move easily)
- ❌ More complex than script approach

### Security
- 🔐 Secrets encrypted client-side before commit
- 🔐 Only cluster controller can decrypt
- 🔐 Original env vars never stored

**Installation**:
```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

See [sealed-secrets/README.md](sealed-secrets/README.md) for details.

---

## 3. External Secrets Operator

**📁 Directory**: `./external-secrets/`

### When to Use
- ✅ Production environments
- ✅ Already using cloud secret managers (AWS, GCP, Azure)
- ✅ Need centralized secret management
- ✅ Want automatic secret rotation
- ✅ Require audit logging and access control

### How It Works
```bash
# 1. Store secret in cloud provider
aws secretsmanager create-secret \
  --name prod/trend-platform/openai-api-key \
  --secret-string "$OPENAI_API_KEY"

# 2. Create SecretStore (connects to cloud)
kubectl apply -f external-secrets/aws-secrets-manager.yaml

# 3. Create ExternalSecret (defines what to sync)
# ESO automatically syncs from cloud → k8s secret

# 4. Secret updates automatically sync!
```

### Pros
- ✅ Single source of truth (cloud secret manager)
- ✅ Automatic sync and rotation
- ✅ Centralized management across all clusters
- ✅ Built-in audit logging (cloud provider)
- ✅ Fine-grained access control (IAM/RBAC)
- ✅ Supports multiple providers

### Cons
- ❌ Requires external secret manager
- ❌ Cloud provider dependency
- ❌ More complex setup
- ❌ Potential vendor lock-in

### Security
- 🔐 Secrets stored in enterprise-grade cloud vault
- 🔐 Access controlled by cloud IAM
- 🔐 All access logged and auditable
- 🔐 Automatic key rotation supported

**Supported Providers**:
- [AWS Secrets Manager](external-secrets/aws-secrets-manager.yaml)
- [Google Secret Manager](external-secrets/google-secret-manager.yaml)
- [Azure Key Vault](external-secrets/azure-key-vault.yaml)
- [HashiCorp Vault](external-secrets/hashicorp-vault.yaml)

**Installation**:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system --create-namespace
```

See [external-secrets/README.md](external-secrets/README.md) for details.

---

## 🔐 Security Pattern (All Approaches)

All three approaches follow the same security principle:

```
Environment Variable (Developer Machine)
    ↓
Script / Tool processes it
    ↓
Kubernetes Secret (Cluster)
    ↓
Application Pod uses it
```

**Never**:
- ❌ Hardcode secrets in YAML files
- ❌ Commit unencrypted secrets to git
- ❌ Store secrets in application code

**Always**:
- ✅ Set secrets as environment variables
- ✅ Use tools to transfer to cluster
- ✅ Rotate secrets regularly

---

## 📋 Decision Matrix

### Choose **Script from Env** if:
- You're just getting started
- You have a small team
- You don't need GitOps
- You want the simplest solution

### Choose **Sealed Secrets** if:
- You want GitOps workflow
- You need audit trail in git
- You don't want cloud dependencies
- You're okay with medium complexity

### Choose **External Secrets** if:
- You're running in production
- You already use cloud secret managers
- You need centralized management
- You want automatic rotation

---

## 🚀 Quick Start Guide

### For Development:
```bash
# Use script approach
export OPENAI_API_KEY='sk-proj-xxxxx'
export POSTGRES_PASSWORD='secure-password'
./create-from-env.sh
```

### For GitOps Teams:
```bash
# Use Sealed Secrets
./sealed-secrets/create-sealed-secrets.sh
git add *-sealed.yaml
git commit && git push
```

### For Production:
```bash
# Use External Secrets
# 1. Store in cloud provider
# 2. Apply SecretStore and ExternalSecret manifests
kubectl apply -f external-secrets/aws-secrets-manager.yaml
```

---

## 📖 Documentation

- [create-from-env.sh](create-from-env.sh) - Simple script approach
- [sealed-secrets/](sealed-secrets/) - Sealed Secrets with GitOps
- [external-secrets/](external-secrets/) - Cloud provider integration
- [../README.md](../README.md) - Kubernetes deployment guide
- [../../docs/SECURITY.md](../../docs/SECURITY.md) - Security best practices

---

## 🆘 Troubleshooting

### Secrets not appearing?

**Script approach**:
```bash
kubectl get secrets -n trend-intelligence
kubectl describe secret api-keys -n trend-intelligence
```

**Sealed Secrets**:
```bash
kubectl get sealedsecrets -n trend-intelligence
kubectl describe sealedsecret api-keys -n trend-intelligence
kubectl logs -n kube-system -l name=sealed-secrets-controller
```

**External Secrets**:
```bash
kubectl get externalsecrets -n trend-intelligence
kubectl describe externalsecret api-keys -n trend-intelligence
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

### Wrong values in secrets?
```bash
# Delete and recreate
kubectl delete secret api-keys -n trend-intelligence

# Then re-run your chosen approach
```

---

**🔐 Remember**: Secrets are only as secure as your handling of environment variables. Never commit real secrets to git!
