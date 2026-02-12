# External Secrets Operator

**Recommended for production deployments**

External Secrets Operator (ESO) syncs secrets from external secret management systems (AWS Secrets Manager, Google Secret Manager, Azure Key Vault, HashiCorp Vault, etc.) into Kubernetes secrets.

## Benefits

✅ **Single Source of Truth**: Secrets managed in cloud provider's secret manager
✅ **Automatic Sync**: ESO automatically updates k8s secrets when cloud secrets change
✅ **Audit Trail**: Cloud providers log all secret access
✅ **Access Control**: Fine-grained IAM/RBAC policies
✅ **Rotation**: Easy secret rotation without redeploying
✅ **GitOps Friendly**: ExternalSecret manifests can be committed (they don't contain secrets)

## Installation

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

Verify installation:
```bash
kubectl get pods -n external-secrets-system
```

## Usage

1. **Set up cloud provider secret manager** (see examples below)
2. **Create SecretStore** (connects to cloud provider)
3. **Create ExternalSecret** (defines which secrets to sync)
4. **Deploy your application** (uses synced k8s secrets)

## Examples

- [AWS Secrets Manager](aws-secrets-manager.yaml)
- [Google Secret Manager](google-secret-manager.yaml)
- [Azure Key Vault](azure-key-vault.yaml)
- [HashiCorp Vault](hashicorp-vault.yaml)

## Documentation

- [External Secrets Operator](https://external-secrets.io/)
- [Provider Guides](https://external-secrets.io/latest/provider/aws-secrets-manager/)
