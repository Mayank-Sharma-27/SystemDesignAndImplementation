

# API Integration Questions from IAM Design

### Question 1: API Key Generation Service

⏱ Time: 50 minutes | 🔧 Pre-built: 40%

**Scenario:**
Your IAM system allows developers to generate API keys with specific scopes. The existing service can create a key ID but doesn’t yet enforce secure storage or permission linking.

**Your Task:**

* Complete the `ApiKeyManager.java` service.
* Implement secure API key generation (public prefix + secret).
* Hash secrets with Argon2 before storage.
* Link the API key to requested permissions via the Authorization Service.
* Return the secret only once to the client.

**Pre-built Components:**

```java
public class ApiKeyRequest {
    private String name;
    private List<String> scopes;
}
```

**Key Requirements:**

* Use a secure random generator for secrets.
* Store only the hash, never the plain-text secret.
* Validate requested scopes against user’s permissions.
* Persist key → permissions mapping in database.

---

### Question 2: API Key Validation Endpoint

⏱ Time: 45 minutes | 🔧 Pre-built: 50%

**Scenario:**
The API Gateway needs to validate incoming API requests by checking API keys against the IAM system. Validation is incomplete.

**Your Task:**

* Complete the `ApiKeyValidator.java` service.
* Implement hash comparison for incoming API secrets.
* Retrieve associated tenant and key permissions.
* Handle revoked/expired API keys.

**Pre-built Components:**

```java
public class ApiRequest {
    private String apiKey;
    private String endpoint;
    private String action; // e.g. "payments:charge"
}
```

**Key Requirements:**

* Perform constant-time comparison for security.
* Return tenant ID and permissions on success.
* Return detailed errors for invalid or revoked keys.
* Add unit tests for validation logic.

---

### Question 3: Permission Change Propagation

⏱ Time: 55 minutes | 🔧 Pre-built: 30%

**Scenario:**
When a user’s role or permission changes, cached data must be invalidated across all API Gateway nodes. Currently, permissions may remain stale.

**Your Task:**

* Complete the `PermissionChangePublisher.java` and `PermissionCacheSubscriber.java`.
* Publish permission change events to Kafka.
* Invalidate affected cache entries in Redis.
* Ensure changes propagate in near real-time.

**Pre-built Components:**

```java
public class PermissionChangeEvent {
    private String keyId;
    private String tenantId;
    private List<String> revokedPermissions;
}
```

**Key Requirements:**

* Serialize/deserialize events to Kafka.
* Implement Redis invalidation with pub/sub.
* Guarantee cache consistency across nodes.

---

### Question 4: Session Authentication Service

⏱ Time: 45 minutes | 🔧 Pre-built: 40%

**Scenario:**
Web users log in and receive short-lived sessions. The existing session service issues tokens but doesn’t integrate with IAM for permission checks.

**Your Task:**

* Complete the `SessionManager.java`.
* Generate JWT-based session tokens.
* Embed user ID, tenant ID, and roles in the token.
* Implement token verification and expiration logic.

**Pre-built Components:**

```java
public class SessionToken {
    private String jwt;
    private Instant expiry;
}
```

**Key Requirements:**

* Use HMAC-SHA256 or RSA for signing tokens.
* Support logout (token blacklist or revocation).
* Integrate with Authorization Service for RBAC enforcement.

---

### Question 5: Audit Logging Service

⏱ Time: 50 minutes | 🔧 Pre-built: 35%

**Scenario:**
The system must log all critical IAM actions (API key creation, permission changes, session revocations). The logging service is partially implemented but not durable.

**Your Task:**

* Complete the `AuditLogger.java` service.
* Write audit events to Kafka.
* Ensure idempotency (no duplicate logs).
* Provide query API to fetch audit logs by user or tenant.

**Pre-built Components:**

```java
public class AuditEvent {
    private String eventType; // e.g., "API_KEY_CREATED"
    private String actorId;
    private String targetId;
    private Instant timestamp;
}
```

**Key Requirements:**

* Guarantee at-least-once delivery to Kafka.
* Ensure audit logs are immutable.
* Add basic retrieval API with pagination.

---

✅ These 5 questions together cover:

* Secure key lifecycle (creation → validation → revocation).
* Permission propagation and cache invalidation.
* Session management with JWTs.
* Durable audit logging.


