# Security Best Practices

This document explains the security patterns used in the AI Trend Intelligence Platform.

---

## 🔐 API Key Management

### The 12-Factor App Pattern

This platform follows the [12-factor app](https://12factor.net/config) methodology for configuration management.

**Core Principle**: Store secrets in environment variables, never in files.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  .env.docker.example (Committed to Git)                     │
│  ├─ Contains: Placeholders and structure                    │
│  ├─ Example: OPENAI_API_KEY=your_api_key_here              │
│  └─ Safe to commit: ✅                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ setup.sh copies to
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  .env.docker (Ignored by Git)                               │
│  ├─ Contains: Same placeholders                             │
│  ├─ Created automatically by setup.sh                       │
│  └─ Never committed: Blocked by .gitignore                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Docker Compose reads
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Environment Variables (Runtime)                            │
│  ├─ Source: export OPENAI_API_KEY='sk-proj-real-key'       │
│  ├─ Used by: Docker containers at runtime                   │
│  └─ Never persisted to disk                                 │
└─────────────────────────────────────────────────────────────┘
```

### Setting Environment Variables

**Temporary (Current Session Only)**:
```bash
export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'
export YOUTUBE_API_KEY='your-youtube-key'
./setup.sh
```

**Permanent (Recommended)**:
```bash
# Add to ~/.bashrc (or ~/.zshrc for zsh)
echo "export OPENAI_API_KEY='sk-proj-xxxxxxxxxxxxx'" >> ~/.bashrc
echo "export YOUTUBE_API_KEY='your-youtube-key'" >> ~/.bashrc
source ~/.bashrc

# Verify
echo $OPENAI_API_KEY
```

**Production (Docker Swarm/Kubernetes)**:
```bash
# Docker Swarm secrets
docker secret create openai_api_key /path/to/key.txt

# Kubernetes secrets
kubectl create secret generic api-keys \
  --from-literal=openai-api-key='sk-proj-xxxxx'
```

---

## ✅ What This Prevents

### 1. Accidental Git Commits
❌ **Without environment variables**:
```bash
# Developer accidentally commits
git add .env.docker
git commit -m "Add config"
git push
# 🚨 API key is now in git history forever!
```

✅ **With environment variables**:
```bash
# Even if .env.docker is committed by mistake
cat .env.docker
# OPENAI_API_KEY=your_api_key_here  (placeholder only)
# ✅ No real secrets exposed!
```

### 2. Cross-Environment Security
❌ **Without environment variables**:
```
Same .env.docker with hardcoded keys used in:
- Developer laptop (dev key)
- Staging server (staging key)
- Production server (prod key)

Result: Wrong keys in wrong environments!
```

✅ **With environment variables**:
```
Same .env.docker.example everywhere (placeholders)
Different environment variables per environment:
- Dev:    export OPENAI_API_KEY='sk-proj-dev-xxx'
- Staging: export OPENAI_API_KEY='sk-proj-staging-xxx'
- Prod:    export OPENAI_API_KEY='sk-proj-prod-xxx'

Result: Correct keys in correct environments!
```

### 3. Easy Key Rotation
❌ **Without environment variables**:
```bash
# Key compromised! Need to update:
1. Edit .env.docker
2. Commit changes
3. Pull on all servers
4. Restart services
```

✅ **With environment variables**:
```bash
# Key compromised! Just update env var:
export OPENAI_API_KEY='sk-proj-new-key'
docker compose restart
# Done! No code changes needed.
```

---

## 🛡️ Additional Security Measures

### 1. Docker Compose Security

The platform uses Docker Compose's built-in environment variable resolution:

```yaml
# docker-compose.yml
services:
  web:
    environment:
      # Reads from environment variable first,
      # falls back to .env.docker if not set
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

**Resolution Order**:
1. Environment variable on host (highest priority)
2. Docker Compose environment section
3. `.env.docker` file (lowest priority, placeholders only)

### 2. .gitignore Protection

```gitignore
# Ignore files that might contain secrets
.env
.env.docker
*.env.local

# But include the template
!.env.docker.example
```

This ensures:
- ✅ `.env.docker.example` is committed (template)
- ❌ `.env.docker` is never committed (local copy)
- ❌ `.env` is never committed (legacy pattern)

### 3. Setup Script Validation

The `setup.sh` script enforces this pattern:

```bash
# Checks for environment variable
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY environment variable not set"
    echo "Set it with: export OPENAI_API_KEY='your-key'"
    exit 1
fi

# Never prompts to edit .env.docker
# ✅ Correct: Forces environment variable usage
```

---

## 📋 Checklist for Developers

Before committing code:

- [ ] Verified `.env.docker.example` contains only placeholders
- [ ] Tested that app works with environment variables
- [ ] Documented any new required environment variables
- [ ] Added new env vars to `.env.docker.example` with placeholders
- [ ] Never committed `.env.docker` (check with `git status`)
- [ ] Secrets are set in `~/.bashrc` or CI/CD secrets

Before deploying:

- [ ] All required environment variables are set on target system
- [ ] Environment variables are different per environment (dev/staging/prod)
- [ ] Secrets are stored in secure secret management (Vault, AWS Secrets Manager, etc.)
- [ ] `.env.docker` is not present on production servers (use env vars only)

---

## ☸️ Kubernetes Deployment Security

### Overview

Kubernetes deployments follow the same security principle: **secrets come from environment variables, never hardcoded in files**.

### Kubernetes Secret Management

Unlike Docker Compose which reads environment variables directly, Kubernetes uses a two-step process:

```
Environment Variable → Kubernetes Secret → Pod
```

### Three Production Approaches

#### 1. Script from Environment Variables (Development/Quick Start)

**Use when**: Development, testing, small teams

```bash
# Set environment variables
export OPENAI_API_KEY='sk-proj-xxxxx'
export POSTGRES_PASSWORD='secure-password'

# Create k8s secrets
cd k8s/secrets
./create-from-env.sh
```

**Flow**:
```
Dev Machine: export OPENAI_API_KEY='key'
    ↓
Script: kubectl create secret ... --from-literal=openai-api-key="$OPENAI_API_KEY"
    ↓
K8s Cluster: Secret stored in etcd (encrypted at rest)
    ↓
Pod: Mounts secret as env var or file
```

**Pros**:
- ✅ Simple and fast
- ✅ No additional tools
- ✅ Cloud agnostic

**Cons**:
- ❌ Not declarative (manual process)
- ❌ Secrets not tracked in git

**Security**: Secrets stored only in k8s etcd, never in git

#### 2. Sealed Secrets (GitOps)

**Use when**: GitOps workflows (ArgoCD, Flux), want audit trail

```bash
# 1. Install controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 2. Create sealed secret from env var
export OPENAI_API_KEY='sk-proj-xxxxx'
cd k8s/secrets/sealed-secrets
./create-sealed-secrets.sh

# 3. Commit encrypted secret (safe!)
git add api-keys-sealed.yaml
git commit -m "Add encrypted secrets"
```

**Flow**:
```
Dev Machine: export OPENAI_API_KEY='key'
    ↓
Script: Creates plain secret (not applied)
    ↓
kubeseal: Encrypts with cluster public key → SealedSecret
    ↓
Git: Commit encrypted SealedSecret ✅ (safe to commit!)
    ↓
Controller: Decrypts with cluster private key → K8s Secret
    ↓
Pod: Uses regular k8s secret
```

**Pros**:
- ✅ GitOps friendly (encrypted secrets in git)
- ✅ Declarative (managed as code)
- ✅ Audit trail in git history
- ✅ Cloud agnostic

**Cons**:
- ❌ Requires controller installation
- ❌ Secrets tied to specific cluster

**Security**:
- Secrets encrypted client-side with cluster public key
- Only cluster controller has private key to decrypt
- Encrypted secrets safe to commit

#### 3. External Secrets Operator (Production/Enterprise)

**Use when**: Production, using cloud secret managers, need centralized management

```bash
# 1. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system --create-namespace

# 2. Store secret in cloud provider
export OPENAI_API_KEY='sk-proj-xxxxx'
aws secretsmanager create-secret \
  --name prod/trend-platform/openai-api-key \
  --secret-string "$OPENAI_API_KEY"

# 3. Create SecretStore and ExternalSecret
kubectl apply -f k8s/secrets/external-secrets/aws-secrets-manager.yaml
```

**Flow**:
```
Dev Machine: export OPENAI_API_KEY='key'
    ↓
CLI: Store in cloud secret manager (AWS/GCP/Azure)
    ↓
Git: Commit SecretStore + ExternalSecret manifests ✅ (no secrets!)
    ↓
ESO Controller: Syncs from cloud → K8s Secret
    ↓
Pod: Uses regular k8s secret
```

**Supported Providers**:
- AWS Secrets Manager
- Google Secret Manager
- Azure Key Vault
- HashiCorp Vault

**Pros**:
- ✅ Single source of truth (cloud secret manager)
- ✅ Automatic sync and rotation
- ✅ Centralized management across clusters
- ✅ Enterprise audit logging (cloud provider)
- ✅ Fine-grained IAM/RBAC access control

**Cons**:
- ❌ Cloud provider dependency
- ❌ More complex setup
- ❌ Requires external secret manager

**Security**:
- Secrets stored in enterprise-grade cloud vault
- Access controlled by cloud IAM
- All access logged and auditable
- Automatic key rotation supported

### Comparison Table

| Feature | Script from Env | Sealed Secrets | External Secrets |
|---------|-----------------|----------------|------------------|
| **Complexity** | ⭐ Low | ⭐⭐ Medium | ⭐⭐⭐ High |
| **GitOps** | ❌ No | ✅ Yes | ✅ Yes |
| **Cloud Agnostic** | ✅ Yes | ✅ Yes | ⚠️ Depends |
| **Automatic Sync** | ❌ No | ❌ No | ✅ Yes |
| **Audit Trail** | ❌ No | ✅ Git history | ✅ Cloud logs |
| **Secret Rotation** | Manual | Manual | Automatic |
| **Best For** | Dev/Test | GitOps teams | Production |

### Security Best Practices

#### Never Do This

❌ **Hardcoded secrets in manifests**:
```yaml
# ❌ WRONG
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
data:
  openai-api-key: c2stcHJvai14eHh4eA==  # base64 of real key
```

❌ **Committing unencrypted secrets**:
```bash
# ❌ WRONG
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="sk-proj-real-key" \
  -o yaml > api-keys.yaml
git add api-keys.yaml  # DON'T DO THIS!
```

#### Always Do This

✅ **Use environment variables**:
```bash
# ✅ CORRECT
export OPENAI_API_KEY='sk-proj-xxxxx'
./create-from-env.sh
# Or: Store in cloud secret manager
# Or: Encrypt with kubeseal
```

✅ **Commit only placeholders or encrypted secrets**:
```bash
# ✅ CORRECT - Template with placeholders
git add k8s/base/secrets.yaml  # Contains "PLACEHOLDER_BASE64_VALUE"

# ✅ CORRECT - Encrypted SealedSecret
git add api-keys-sealed.yaml  # Encrypted, safe to commit

# ✅ CORRECT - ExternalSecret manifest (no secrets)
git add external-secrets.yaml  # References cloud secret manager
```

### Kubernetes Deployment Checklist

Before deploying to Kubernetes:

- [ ] Environment variables set (never hardcoded in files)
- [ ] Chosen secret management approach (script/sealed/external)
- [ ] Secrets created in cluster (or cloud provider)
- [ ] Verified secrets exist: `kubectl get secrets -n trend-intelligence`
- [ ] Template files (`secrets.yaml`) not applied directly
- [ ] Only encrypted/reference files committed to git
- [ ] Access controls configured (RBAC, network policies)
- [ ] Secrets encrypted at rest in etcd

Production-specific:

- [ ] Using External Secrets Operator or Sealed Secrets
- [ ] Secrets stored in enterprise secret manager (AWS/GCP/Azure/Vault)
- [ ] IAM/RBAC policies restrict secret access
- [ ] Audit logging enabled
- [ ] Secret rotation plan in place
- [ ] Different secrets per environment (dev/staging/prod)

### Verifying Kubernetes Secrets

```bash
# List secrets
kubectl get secrets -n trend-intelligence

# Check secret contents (base64 encoded)
kubectl get secret api-keys -n trend-intelligence -o jsonpath='{.data.openai-api-key}' | base64 -d

# Describe secret (metadata only, no values)
kubectl describe secret api-keys -n trend-intelligence

# Check if pod has access to secret
kubectl exec -n trend-intelligence <pod-name> -- env | grep OPENAI_API_KEY
```

### Rotating Kubernetes Secrets

#### Script Approach
```bash
# 1. Update environment variable
export OPENAI_API_KEY='sk-proj-new-key'

# 2. Delete old secret
kubectl delete secret api-keys -n trend-intelligence

# 3. Recreate
./k8s/secrets/create-from-env.sh

# 4. Restart pods to pick up new secret
kubectl rollout restart deployment -n trend-intelligence
```

#### External Secrets Approach
```bash
# 1. Update secret in cloud provider
aws secretsmanager update-secret \
  --secret-id prod/trend-platform/openai-api-key \
  --secret-string "sk-proj-new-key"

# 2. Wait for ESO to sync (automatic, ~1 min)
# Or force sync:
kubectl annotate externalsecret api-keys force-sync=$(date +%s) -n trend-intelligence

# 3. Restart pods
kubectl rollout restart deployment -n trend-intelligence
```

### Documentation

- **[k8s/README.md](../k8s/README.md)** - Kubernetes deployment guide
- **[k8s/secrets/README.md](../k8s/secrets/README.md)** - Complete secrets comparison
- **[k8s/secrets/external-secrets/](../k8s/secrets/external-secrets/)** - External Secrets examples
- **[k8s/secrets/sealed-secrets/](../k8s/secrets/sealed-secrets/)** - Sealed Secrets examples

---

## 🔍 Auditing Secrets

### Check if Secrets are in Git History

```bash
# Search git history for potential secrets
git log -p | grep -i "api.key\|secret\|password" | head -20

# Check specific file history
git log -p -- .env.docker

# If secrets found, they must be rotated immediately!
```

### Verify Current Configuration

```bash
# Check what's in the committed template
cat .env.docker.example | grep API_KEY
# Should show: OPENAI_API_KEY=your_api_key_here

# Check local copy (should be same)
cat .env.docker | grep API_KEY
# Should show: OPENAI_API_KEY=your_api_key_here

# Check actual runtime value
echo $OPENAI_API_KEY
# Should show: sk-proj-real-key-here
```

---

## 🚨 What To Do If Secrets Are Exposed

If API keys or secrets are accidentally committed to git:

### 1. Rotate Keys Immediately
```bash
# Get new API key from provider
# Update environment variable
export OPENAI_API_KEY='sk-proj-NEW-KEY'

# Restart services
docker compose restart
```

### 2. Revoke Compromised Keys
- OpenAI: https://platform.openai.com/api-keys
- Delete the compromised key immediately

### 3. Clean Git History (if needed)
```bash
# ⚠️ Requires force push, coordinate with team!

# Remove sensitive file from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env.docker" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (dangerous!)
git push origin --force --all
```

### 4. Notify Team
- Inform all developers to rotate their keys
- Update CI/CD secrets
- Review access logs for unauthorized usage

---

## 📚 References

- [The Twelve-Factor App: Config](https://12factor.net/config)
- [OWASP: Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Docker: Use secrets with Compose](https://docs.docker.com/compose/use-secrets/)
- [GitHub: Remove sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

## 💡 Summary

**Golden Rule**: If a value is secret, it comes from an environment variable, never from a file.

**File Roles**:
- `.env.docker.example`: Template with placeholders (committed)
- `.env.docker`: Local copy with placeholders (ignored)
- Environment variables: Real secrets (runtime only)

**Developer Workflow**:
```bash
# 1. Clone repo
git clone <repo>

# 2. Set secrets in environment
export OPENAI_API_KEY='real-key'

# 3. Run setup (creates .env.docker from template)
./setup.sh

# 4. Develop with confidence - secrets never touch disk!
```

**✅ Result**: Secrets are secure, never committed, and easy to rotate!
