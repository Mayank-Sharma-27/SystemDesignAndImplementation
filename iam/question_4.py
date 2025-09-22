"""
Q4: Cache Invalidation Simulator

Background:
-----------
In the Auth Service, authorization decisions (`ALLOW` / `DENY`) are cached
for performance in Redis. When permissions change (e.g., a role loses a permission),
we must invalidate affected cache entries in near real time.

Input Example:
--------------
{
  "cache": {"sk_live_abc:payments:create": "ALLOW"},
  "event": {
    "type": "ROLE_PERMISSION_REMOVED",
    "role_id": "role_dev",
    "permission": "payments:create"
  },
  "role_assignments": {"sk_live_abc": "role_dev"}
}

Parts:
------

Part 1 (15 min):
    - On receiving a permission change event, delete affected cache entries.
    - Example: if "payments:create" was removed from role_dev,
      and sk_live_abc is assigned role_dev,
      then "sk_live_abc:payments:create" must be removed from cache.

Part 2 (15 min):
    - Support multiple roles per key.
    - Example: if sk_live_xyz has roles [role_dev, role_viewer],
      then invalidation should target all matching role → permission combos.

Part 3 (15 min):
    - Track metrics:
        * Number of invalidations performed per event.
        * Final cache size after purge.
    - Output should include both the updated cache and metrics.

Expected Behavior:
------------------
- Input: a cache dict, an event (role+permission removed), and role assignments.
- Output: updated cache with affected entries removed + metrics.
"""


class CacheInvalidation:
    
    def invalidate_cache(self, data: dict) -> dict:
        cache = data["cache"]
        event = data["event"]
        role_assignments = data["role_assignments"]
        
        role_id = event["role_id"]
        permission = event["permission"]
        timestamp = event.get("timestamp")
        affected_users = {user for user, roles in role_assignments.items() if role_id in roles}
        
        new_cache = {
            key: value
            for key, value in cache.items()
            if not (key.split(":",1)[0] in affected_users and key.endswith(f":{permission}"))
        }
        invalidations = len(cache) - len(new_cache)
        time_window = 1  
        invalidations_per_second = invalidations/ time_window if time_window > 0 else 0           
                         
        return {
        "cache" : new_cache,
        "metrics": {    
        "invalidations": invalidations,
        "cache_size_after": len(new_cache),
        "invalidations_per_second": invalidations_per_second
        }
       }  

data = {
  "cache": {
    "sk_live_abc:payments:create": "ALLOW",
    "sk_live_abc:invoices:read": "ALLOW",
    "sk_live_xyz:payments:create": "ALLOW",
    "sk_live_xyz:invoices:read": "ALLOW",
    "sk_live_pqr:payments:create": "ALLOW"
  },
  "event": {
    "type": "ROLE_PERMISSION_REMOVED",
    "role_id": "role_dev",
    "permission": "payments:create"
  },
  "role_assignments": {
    "sk_live_abc": ["role_dev"], 
    "sk_live_xyz": ["role_dev", "role_viewer"],
    "sk_live_pqr": ["role_admin"]
  }
}

cache_invalidation = CacheInvalidation()

print(cache_invalidation.invalidate_cache(data))
                            
