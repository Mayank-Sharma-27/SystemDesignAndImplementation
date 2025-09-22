
from datetime import datetime
class Verification:
    
    def _get_prinipal_type(self,data: dict) -> str:
        if data.get("user_id"):
            return "human"
        return "machine"    
    
    def verify_credentails(self, data: dict) -> dict:
        credentials = data["credentials"]
        
        jwt_sessions = data["jwt_sessions"]
        api_keys = data["api_keys"]
        response = []
        current_time = datetime.now()
        for credential in credentials:
            principal_type = self._get_prinipal_type(credential) 
            type = credential["type"]
            if type == "jwt":
                token = credential.get("token")
                session = jwt_sessions.get("token")
                if not session:
                    response.append({"crendentaial": token, "valid": False, "reason": "Unknown"})
                expiry_time = datetime.fromtimestamp(jwt_sessions[token]["expires_at"])
                if current_time >= expiry_time:
                    response.append({
                        "credential": token,
                        "valid": False,
                        "reason": "JWT expired",
                        "principal_type": principal_type
                    })
                else:
                    response.append({
                        "credential": token,
                        "valid": True,
                        "principal_type": principal_type
                    })
            elif type == "api_key" and credential.get("key_id"):
                id = credential["key_id"]
                if api_keys[id]["revoked"]:
                    response.append({
                        "credential": id,
                        "valid": False,
                        "response": "API key revoked",
                        "principal_type": principal_type
                    })
                else:
                    response.append({
                        "credential": id,
                        "valid": True,
                        "principal_type": principal_type
                    })
        
        return response
    
data = {
  "credentials": [
    {"type": "jwt", "token": "jwt_abc", "user_id": "u1"},
    {"type": "api_key", "key_id": "sk_live_abc", "tenant_id": "acme_corp"},
    {"type": "jwt", "token": "jwt_expired", "user_id": "u2"},
    {"type": "api_key", "key_id": "sk_revoked", "tenant_id": "acme_corp"}
  ],
  "jwt_sessions": {
    "jwt_abc": {"user_id": "u1", "expires_at": 2000000000},
    "jwt_expired": {"user_id": "u2", "expires_at": 1500000000}
  },
  "api_keys": {
    "sk_live_abc": {"scopes": ["invoices:read"], "revoked": False},
    "sk_revoked": {"scopes": ["payments:create"], "revoked": True}
  }
}

verification = Verification()
print(verification.verify_credentails(data))                
                
                        
                        
                