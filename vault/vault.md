# Vault Cheat Sheet

Standing up a Vault-backed app means wiring four things in order: where secrets live, who is allowed to read them, how a human authenticates, and how a machine authenticates. Skip a step and the next one has nothing to attach to.

---

## Secrets Engines

**Nothing can be written until a secrets engine is mounted at a path. KV v2 is the default choice — it gives you versioning for free.**

```bash
# Enable a KV version 2 secrets engine at a custom path
vault secrets enable -path=kv-<APP> kv-v2
```

---

## Policies

**A policy is just an HCL document naming paths and capabilities — write it once, attach it to every auth method that needs it.**

```bash
# Create or update a policy, reading the HCL document from stdin
vault policy write <APP>-admin -
```

---

## Auth Methods — userpass

**For human operators, userpass is the low-ceremony option: enable the method once, then create one user per person.**

```bash
# Enable the userpass authentication method
vault auth enable userpass

# Create a user and attach a policy to it
vault write auth/userpass/users/admin-<APP> password="<PASSWORD>" policies="<APP>-admin"
```

---

## AppRole — Machine Authentication

**Services can't type a password. AppRole splits the credential in two — a RoleID that identifies the role and a SecretID that proves possession — so each half can be distributed and rotated separately.**

```bash
# Create the role, with the policy and TTLs it will hand out on login
vault write auth/approle/role/<APP>-backend-role token_policies="<APP>-app" token_ttl=1h token_max_ttl=4h

# Read the RoleID — stable, safe to bake into config
vault read auth/approle/role/<APP>-backend-role/role-id

# Generate a SecretID — treat this like a password, distribute out-of-band
vault write -f auth/approle/role/<APP>-backend-role/secret-id
```

---

## Key Patterns

| Symptom | Move |
|---|---|
| No path to write secrets to | `vault secrets enable -path=kv-<APP> kv-v2` |
| A method needs an access policy before it's useful | `vault policy write <APP>-admin -` from HCL on stdin |
| Human operator needs a login | `vault auth enable userpass` once, then one `vault write auth/userpass/users/...` per person |
| A service needs to authenticate, not a person | AppRole: create role, read `role-id`, generate `secret-id` |
| SecretID compromised or rotated | Re-run `vault write -f .../secret-id` — RoleID stays the same |
