"""
Q2: Authorization Decision Engine

Background:
-----------
This service implements the hot-path authorization check for an IAM system.
For every incoming API request, it must decide quickly:

    "Can this principal perform this action in this tenant?"

The solution is broken down into three parts:

Part 1:
    - Validate the key exists and is not revoked.
    - Return ALLOW if the requested action is in the key’s scopes, otherwise DENY.

Part 2:
    - Enforce tenant isolation.
    - Only allow requests if the tenant_id in the request matches the tenant_id bound to the key.

Part 3:
    - Support real-time permission updates via events.
    - Handle REVOKE events (remove a permission from the key’s scopes).
    - Handle GRANT events (add a permission to the key’s scopes).
    - Ensure idempotency (duplicate events don’t break state).
    - If a key is revoked, events are ignored.

Inputs:
-------
- request: contains key_id, action, tenant_id
- keys: dictionary of key metadata (scopes, tenant_id, revoked flag)
- events: dictionary describing permission changes (REVOKE or GRANT)

Outputs:
--------
- validate_request returns a decision: ALLOW or DENY with reason.
- apply_event updates key scopes and returns status: updated or ignored with reason.
"""


class AuthService:
    
    def apply_event(self, data: dict, events: dict) -> dict:
        keys = data["keys"]
        event_key_id = events["key_id"]
        event = events["event"]
        permission = events["permission"]
        
        if event_key_id in keys:
            key = keys[event_key_id]
            revoked = key["revoked"]
            scopes = key["scopes"]
            if revoked:
                return  {"status": "ignored", "message" :"key already revoled"}
            if event == "REVOKE":
                if permission in scopes:
                    keys[event_key_id]["scopes"].remove(permission)
                    return {"status": "updated", "reason": f"Revoked {permission}"}
                else:
                    return {"status": "ignored", "reason": f"Permission {permission} as not there"}
            elif event == "GRANT": 
                if permission not in scopes:
                    keys[event_key_id]["scopes"].append(permission)
                    return {"status": "updated", "reason": f"Added {permission}"}
                else:
                    return {"status": "ignored", "reason": f"Permission {permission} already there"}
                          
    def validate_request(self, data: dict) -> dict:
        request = data["request"]
        keys = data["keys"]
        
        key_id = request["key_id"]
        action = request["action"]
        tenant_id = request["tenant_id"]
        
        if key_id not in keys:
            return {"decision": "DENY", "reason": "Key not found"}
        
        key_info = keys[key_id]
        scopes = key_info["scopes"]
        revoked = key_info["revoked"]
        tenant_id_in_key = key_info["tenant_id"]
        
        if tenant_id_in_key != tenant_id:
            return {
                "decision": "DENY",
                "reason": f"Tenant mismatch: key belongs to {tenant_id_in_key} but request is for {tenant_id}"
            }
        
        if revoked:
            return {"decision": "DENY", "reason": "Key revoked"}
        
        if action not in scopes:
            return {
                "decision": "DENY",
                "reason": f"Action {action} not in scopes granted to key"
            }
        
        return {"decision": "ALLOW", "reason": f"Action {action} is in key scopes"}

                 

auth_service = AuthService()

# Base state: one active key
data = {
  "request": {"key_id": "sk_live_abc", "action": "payments:create", "tenant_id": "acme_corp"},
  "keys": {
    "sk_live_abc": {
      "scopes": ["payments:create", "invoices:read"],
      "tenant_id": "acme_corp",
      "revoked": False
    }
  }
}

print("=== Initial Allow ===")
print(auth_service.validate_request(data))
# -> ALLOW

print("\n=== Action Not in Scopes ===")
req = {"request": {"key_id": "sk_live_abc", "action": "customers:write", "tenant_id": "acme_corp"}, "keys": data["keys"]}
print(auth_service.validate_request(req))
# -> DENY (action not in scopes)

print("\n=== Tenant Mismatch ===")
req = {"request": {"key_id": "sk_live_abc", "action": "payments:create", "tenant_id": "beta_inc"}, "keys": data["keys"]}
print(auth_service.validate_request(req))
# -> DENY (tenant mismatch)

print("\n=== Revoke Key ===")
data["keys"]["sk_live_abc"]["revoked"] = True
print(auth_service.validate_request(data))
# -> DENY (key revoked)

# Reset revoked state for event testing
data["keys"]["sk_live_abc"]["revoked"] = False

print("\n=== Apply REVOKE Event (payments:create) ===")
event1 = {"event": "REVOKE", "key_id": "sk_live_abc", "permission": "payments:create"}
print(auth_service.apply_event(data, event1))

print("\n=== Check After REVOKE Event ===")
print(auth_service.validate_request(data))
# -> DENY

print("\n=== Apply REVOKE Event Again (idempotency) ===")
print(auth_service.apply_event(data, event1))
# -> ignored (was not there)

print("\n=== Apply GRANT Event (customers:write) ===")
event2 = {"event": "GRANT", "key_id": "sk_live_abc", "permission": "customers:write"}
print(auth_service.apply_event(data, event2))
# -> updated (added customers:write)

print("\n=== Check After GRANT Event ===")
req = {"request": {"key_id": "sk_live_abc", "action": "customers:write", "tenant_id": "acme_corp"}, "keys": data["keys"]}
print(auth_service.validate_request(req))
# -> ALLOW

print("\n=== Apply GRANT Event Again (idempotency) ===")
print(auth_service.apply_event(data, event2))
# -> ignored (already present)

print("\n=== Apply Event for Nonexistent Key ===")
event3 = {"event": "GRANT", "key_id": "sk_live_xyz", "permission": "payments:create"}
print(auth_service.apply_event(data, event3))
# -> ignored (key not found)

             