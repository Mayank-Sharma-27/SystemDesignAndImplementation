""""
Q3: Role-to-Permission Expansion

Background:
-----------
In an IAM system, users are assigned roles, and roles map to permissions.
API keys may request a scoped subset of these permissions. The engine must
expand roles into permissions and validate API key scopes.

Input Example:
--------------
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

Parts:
------

Part 1 (15 min):
    - Expand each user into a list of permissions based on their roles.
    - Example: user u1 with role "admin" → ["payments:create", "invoices:read", "customers:write"]

Part 2 (15 min):
    - Support multi-role union.
    - Example: user u2 with roles ["viewer", "admin"] → union of both role permissions
      = ["payments:create", "invoices:read", "customers:write"]

Part 3 (15 min):
    - Validate API key requested scopes.
    - Ensure requested scopes ⊆ user’s full permissions.
    - Reject invalid scope requests with a clear reason.

"""


class Roles:
    
    def show_permissions(self, data: dict) -> dict:
        if not data["roles"] or not data["tenant_users"]:
            raise ValueError("Invalid input")
        roles = data["roles"]
        tenant_users = data["tenant_users"]
        user_explanded_roles = []
        for user in tenant_users:
            user_id, user_roles = user["user_id"], user["roles"]
            user_all_roles = set()
            for role in user_roles:
                if role not in roles:
                    continue
                user_all_roles.update(roles[role])
                    
            user_explanded_roles.append({
                    "user_id": user_id,
                    "permissions": list(user_all_roles)
                })
        return user_explanded_roles
    
    def validate_requests(self, data: dict) -> dict:
        user_explanded_roles = self.show_permissions(data)
        api_key_requests = data["api_key_requests"]
        
        user_id_roles = {}
        for user_role in user_explanded_roles:
            user_id, permissions  = user_role["user_id"], user_role["permissions"]
            user_id_roles[user_id] = permissions
        result = []
        for request in api_key_requests:
            user_id, requested_scopes = request["user_id"], request["requested_scopes"]
            
            if user_id in user_id_roles:
                if set(requested_scopes).issubset(user_id_roles[user_id]):
                    result.append({
                        "user_id": user_id,
                        "status": "APPROVED",
                        "granted_scopes": requested_scopes
                    })
                else:
                    result.append({
                        "user_id": user_id,
                        "status": "Rejected",
                        "granted_scopes": f"Requested scopes: {requested_scopes} exceeds user permisisons"
                    })             
         
        return result           





roles = Roles()
print("----Part1----")
data = {
  "roles": {
    "admin": ["payments:create", "invoices:read", "customers:write"],
    "viewer": ["invoices:read"]
  },
  "tenant_users": [
    {"user_id": "u1", "roles": ["admin"]},
    {"user_id": "u2", "roles": ["viewer"]}
  ]
}
print(roles.show_permissions(data))  
print("----Part2----")               
data = {
  "roles": {
    "admin": ["payments:create", "invoices:read", "customers:write"],
    "viewer": ["invoices:read"],
    "developer": ["payments:create", "code:deploy"]
  },
  "tenant_users": [
    {"user_id": "u1", "roles": ["admin"]},
    {"user_id": "u2", "roles": ["viewer", "admin"]},
    {"user_id": "u3", "roles": ["developer", "viewer"]}
  ]
}
print(roles.show_permissions(data))  
print("----Part3----")
data = {
  "roles": {
    "admin": ["payments:create", "invoices:read", "customers:write"],
    "viewer": ["invoices:read"]
  },
  "tenant_users": [
    {"user_id": "u1", "roles": ["admin"]},
    {"user_id": "u2", "roles": ["viewer", "admin"]}
  ],
  "api_key_requests": [
    {"user_id": "u1", "requested_scopes": ["payments:create"]},
    {"user_id": "u2", "requested_scopes": ["customers:write", "invoices:read"]},
    {"user_id": "u2", "requested_scopes": ["code:deploy"]}
  ]
}

print(roles.validate_requests(data))

                
                
        
        
        