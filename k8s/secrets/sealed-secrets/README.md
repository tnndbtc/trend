# Sealed Secrets

**GitOps-friendly secret management**

Sealed Secrets allows you to encrypt secrets locally and commit them to git. Only the cluster can decrypt them.

## Benefits

✅ **GitOps Friendly**: Encrypted secrets can be committed to git
✅ **Declarative**: Secrets managed as code in version control
✅ **Simple**: No external dependencies (cloud providers, Vault, etc.)
✅ **Secure**: Secrets encrypted with cluster-specific key
✅ **Audit Trail**: Changes tracked in git history

## How It Works

```
Developer Machine:
  1. Create secret (from env var)
  2. Encrypt with kubeseal → SealedSecret
  3. Commit SealedSecret to git ✅

Kubernetes Cluster:
  4. Controller decrypts SealedSecret
  5. Creates regular Kubernetes Secret
  6. Application uses the secret
```

## Installation

```bash
# Install controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar -xvzf kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

Verify installation:
```bash
kubectl get pods -n kube-system | grep sealed-secrets
```

## Usage

### 1. Create Secret from Environment Variable

```bash
# Set your API key
export OPENAI_API_KEY='sk-proj-xxxxx'

# Create secret manifest (not applied yet)
kubectl create secret generic api-keys \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --dry-run=client \
  -o yaml > secret.yaml
```

### 2. Encrypt with kubeseal

```bash
# Encrypt the secret
kubeseal -f secret.yaml -w sealed-secret.yaml -n trend-intelligence

# Delete unencrypted secret
rm secret.yaml

# Now sealed-secret.yaml is safe to commit!
git add sealed-secret.yaml
git commit -m "Add encrypted API key"
```

### 3. Apply to Cluster

```bash
kubectl apply -f sealed-secret.yaml -n trend-intelligence
```

The controller will automatically:
1. Decrypt the SealedSecret
2. Create a regular Kubernetes Secret
3. Your pods can use it normally

## Helper Script

Use our helper script to create all secrets from environment variables:

```bash
# Set environment variables
export OPENAI_API_KEY='sk-proj-xxxxx'
export POSTGRES_PASSWORD='secure-password'

# Run script
./create-sealed-secrets.sh
```

This creates encrypted SealedSecrets that are safe to commit.

## Examples

- [api-keys-sealed.yaml](api-keys-sealed.yaml) - Example SealedSecret (encrypted)
- [create-sealed-secrets.sh](create-sealed-secrets.sh) - Script to create all secrets

## Documentation

- [Sealed Secrets GitHub](https://github.com/bitnami-labs/sealed-secrets)
- [User Guide](https://github.com/bitnami-labs/sealed-secrets#usage)
