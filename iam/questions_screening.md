
---

## **IAM Screening Round Questions**

---

### **Q1: API Key Lifecycle Manager**

**Background**
API Keys are long-lived credentials with scoped permissions, but must be revocable and rotated securely.

**Input Example**

```json
{
  "request": {"scopes": ["payments:create", "invoices:read"]},
  "user_permissions": ["payments:create", "invoices:read", "customers:write"],
  "stored_keys": []
}
```

**Part 1 (15 min)**

* Validate requested scopes ⊆ user permissions.
* Generate an API key (public prefix + random secret).
* Store only the hash of the secret. Return plaintext secret once.

**Part 2 (15 min)**

* Add **revocation support**: mark a key as revoked, and validation should fail.

**Part 3 (15 min)**

* Add **rotation**: generate a new secret for the same key without changing scopes.
* Log all lifecycle events (`CREATED`, `REVOKED`, `ROTATED`) into an audit log.

---

### **Q2: Authorization Decision Engine**

**Background**
The system must answer the critical hot-path question: “Can this principal perform this action?”

**Input Example**

```json
{
  "request": {
    "key_id": "sk_live_abc",
    "action": "payments:create",
    "tenant_id": "acme_corp"
  },
  "keys": {
    "sk_live_abc": {
      "scopes": ["payments:create", "invoices:read"],
      "tenant_id": "acme_corp",
      "revoked": false
    }
  }
}
```

**Part 1 (15 min)**

* Validate the key (not revoked, hash matches).
* Return `ALLOW` if action ∈ scopes, else `DENY`.

**Part 2 (15 min)**

* Add **tenant enforcement**: only allow if tenant\_id matches.

**Part 3 (15 min)**

* Support **permission change events** (e.g., `REVOKE payments:create`).
* Update cached scopes in real time when events arrive.

---

### **Q3: Role-to-Permission Expansion**

**Background**
Users hold roles; roles map to permissions; API keys may request scoped subsets.

**Input Example**

```json
{
  "roles": {
    "admin": ["payments:create", "invoices:read", "customers:write"],
    "viewer": ["invoices:read"]
  },
  "tenant_users": [
    {"user_id": "u1", "roles": ["admin"]},
    {"user_id": "u2", "roles": ["viewer", "admin"]}
  ]
}
```

**Part 1 (15 min)**

* Expand each user → list of permissions.

**Part 2 (15 min)**

* Add **multi-role union**: user permissions are the union of all role permissions.

**Part 3 (15 min)**

* Add **API key scope validation**: ensure requested key scopes ⊆ user permissions.
* Reject invalid scope requests.

---

### **Q4: Cache Invalidation Simulator**

**Background**
Your Auth Service caches `ALLOW`/`DENY` decisions in Redis. Permission changes must invalidate cache entries.

**Input Example**

```json
{
  "cache": {"sk_live_abc:payments:create": "ALLOW"},
  "event": {
    "type": "ROLE_PERMISSION_REMOVED",
    "role_id": "role_dev",
    "permission": "payments:create"
  },
  "role_assignments": {"sk_live_abc": "role_dev"}
}
```

**Part 1 (15 min)**

* On receiving a change event, delete affected cache entries.

**Part 2 (15 min)**

* Support multiple roles per key: invalidate all affected entries.

**Part 3 (15 min)**

* Track **metrics**: number of invalidations per second, size of cache after purge.

---

### **Q5: Immutable Audit Log Formatter**

**Background**
All IAM actions must be durable and human-readable for compliance.

**Input Example**

```json
[
  {"event": "API_KEY_CREATED", "user": "u1", "timestamp": 1700000000},
  {"event": "ROLE_ASSIGNED", "user": "u2", "timestamp": 1700000100}
]
```

**Part 1 (15 min)**

* Format logs as `[time] user:event`.

**Part 2 (15 min)**

* Add filtering by user or event type.

**Part 3 (15 min)**

* Add **compliance summary**: counts of key creations, revocations, permission changes.

---

### **Q6 (Bonus): Session Validator**

**Background**
Human users authenticate via JWTs; machine clients use API Keys.

**Input Example**

```json
{
  "credentials": [
    {"type": "jwt", "token": "jwt_abc", "user_id": "u1"},
    {"type": "api_key", "key_id": "sk_live_abc", "tenant_id": "acme_corp"}
  ],
  "jwt_sessions": {"jwt_abc": {"user_id": "u1", "expires_at": 1700000100}},
  "api_keys": {"sk_live_abc": {"scopes": ["invoices:read"], "revoked": false}}
}
```

**Part 1 (15 min)**

* Validate JWT expiry and API key revocation.

**Part 2 (15 min)**

* Add **mixed enforcement**: return `"human"` vs `"machine"` principal type.

**Part 3 (15 min)**

* Expired sessions and revoked keys should be logged into the **audit system**.

---

