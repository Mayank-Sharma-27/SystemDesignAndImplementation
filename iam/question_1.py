import secrets
import hashlib
import time

class Iam:
    
    def hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def current_timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())    
        
    def generate_key(self, data: dict, stored_keys: list, audit_load: list) -> dict:
        request = data["request"]
        requested_scopes = request["scopes"]
        user_permissions = data["user_permissions"]
        
        # Validate scopes
        if not set(requested_scopes).issubset(user_permissions):
            raise ValueError("Requested scopes exceed user permissions")
        
        # Generate IDs
        public_id = "sk_live_" + secrets.token_hex(4)
        secret = secrets.token_hex(16)
        audit_load.append({
            "event": "CREATED",
            "key_id": public_id,
            "timestamp": self.current_timestamp()
        })
        # Store only hash
        key_record = {
            "public_id": public_id,
            "secret_hash": self.hash_secret(secret),
            "scopes": requested_scopes,
            "revoked": False
        }
        stored_keys.append(key_record)
        
        # Return plaintext secret once
        return {
            "public_id": public_id,
            "secret": secret,
            "scopes": requested_scopes
        }
        
    def perform_key_action(self, data: dict, audit_load: list) -> dict:
        public_id = data["public_id"]
        stored_keys = data["stored_keys"]
        action = data["action"]
        for key in stored_keys:
            if public_id == key["public_id"]:
                if action == "revoke":
                    if key["revoked"]:
                        return {"public_id": public_id, "revoked": True, "message": "Already revoked"}
                    key["revoked"] = True
                    audit_load.append({
                "event": "REVOKED",
                "key_id": public_id,
                "timestamp": self.current_timestamp()
            })
                    return {"public_id": public_id, "revoked": True, "message": "Key successfully revoked"}
                elif action == "rotate":
                    if key["revoked"]:
                        return {"public_id": public_id, "revoked": True, "message": "Already revoked"}
                    
                    new_secret = secrets.token_hex(16)
                    key["secret_hash"] = self.hash_secret(new_secret)
                    audit_load.append({
                "event": "ROTATED",
                "key_id": public_id,
                "timestamp": self.current_timestamp()
            })
                return {"public_id": public_id, "new_secret": key["secret_hash"], "scopes": key["scopes"], "message": "Key successfully rotated"}
                        
            
        return {"public_id": public_id, "revoked": False, "message": "Key not found"}


# Example usage
iam = Iam()
stored_keys = []
audit_log = []

# Part 1: Create
data = {
  "request": {"scopes": ["payments:create", "invoices:read"]},
  "user_permissions": ["payments:create", "invoices:read", "customers:write"],
  "stored_keys": stored_keys
}
resp = iam.generate_key(data, stored_keys, audit_log)
print("=== Part 1: Create Key ===")
print("API Response:", resp)
print("Stored Keys:", stored_keys)
print("Audit Log:", audit_log)
print()

# Part 2: Rotate (before revoking)
data_rotate = {"action": "rotate", "public_id": resp["public_id"], "stored_keys": stored_keys}
rotate_resp = iam.perform_key_action(data_rotate, audit_log)
print("=== Part 2: Rotate Key ===")
print("Rotate Response:", rotate_resp)
print("Stored Keys After Rotate:", stored_keys)
print("Audit Log:", audit_log)
print()

# Part 3: Revoke (after rotation)
data_revoke = {"action": "revoke", "public_id": resp["public_id"], "stored_keys": stored_keys}
revoke_resp = iam.perform_key_action(data_revoke, audit_log)
print("=== Part 3: Revoke Key ===")
print("Revoke Response:", revoke_resp)
print("Stored Keys After Revoke:", stored_keys)
print("Audit Log:", audit_log)