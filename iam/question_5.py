"""
Q5: Immutable Audit Log Formatter

Background:
-----------
All IAM actions (API key lifecycle events, role changes, permission updates)
must be written to an immutable, durable audit log. 
For compliance (SOC 2, PCI, GDPR), logs must also be human-readable.

Input Example:
--------------
[
  {"event": "API_KEY_CREATED", "user": "u1", "timestamp": 1700000000},
  {"event": "ROLE_ASSIGNED", "user": "u2", "timestamp": 1700000100}
]

Parts:
------

Part 1 (15 min):
    - Format each log entry as a human-readable string:
        "[time] user:event"
    - Example: "[2023-11-14T00:00:00Z] u1:API_KEY_CREATED"

Part 2 (15 min):
    - Add filtering by user or event type.
    - Example: Only return logs for `user="u1"` or `event="ROLE_ASSIGNED"`.

Part 3 (15 min):
    - Add a compliance summary.
    - Count specific categories of events:
        * Key creations (API_KEY_CREATED)
        * Key revocations (API_KEY_REVOKED)
        * Permission changes (PERMISSION_GRANTED, PERMISSION_REVOKED, etc.)
    - Output should include both the formatted logs and the summary.
"""

from datetime import datetime
from collections import Counter
class LogParser:
    
    def parse_logs(self, logs: list) -> dict:
        readable_logs = []
        summary = Counter()
        for log in logs:
            event, user, timestamp = log["event"], log["user"], log["timestamp"]
            datetime_string = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%SZ")
            readable_logs.append(f"[{datetime_string}] {user}:{event}")
            # Compliance summary mapping
            if event == "API_KEY_CREATED":
                summary["API_KEY_CREATED"] += 1
            elif event == "API_KEY_REVOKED":
                summary["API_KEY_REVOKED"] += 1
            elif event in ("PERMISSION_GRANTED", "PERMISSION_REVOKED"):
                summary["PERMISSION_CHANGED"] += 1
        
        return {"formatted_logs": readable_logs, "summary": Counter(summary)}
        
    
    def filter_logs(self, data: dict) -> list:
        logs = data["logs"]
        
        readable_logs = self.parse_logs(logs)["formatted_logs"]
        filter_to_apply = data.get("filter", {})
        
        ans = []
        for log in readable_logs:

            log_to_check = log.split(" ")[1]
            user, event = log_to_check.split(":")
            if filter_to_apply.get("user") and filter_to_apply["user"] != user:
                continue
            if filter_to_apply.get("event") and filter_to_apply["event"] != event:
                continue    
            ans.append(log)
        return ans        
            

data = [
    {"event": "API_KEY_CREATED", "user": "u1", "timestamp": 1700000000},
    {"event": "ROLE_ASSIGNED", "user": "u2", "timestamp": 1700000100},
    {"event": "API_KEY_REVOKED", "user": "u1", "timestamp": 1700000200},
    {"event": "PERMISSION_GRANTED", "user": "u3", "timestamp": 1700000300},
    {"event": "PERMISSION_REVOKED", "user": "u3", "timestamp": 1700000400}
  ]

log_parser = LogParser()
print("----Part1----")
print(log_parser.parse_logs(data))       
data = {
  "logs": [
    {"event": "API_KEY_CREATED", "user": "u1", "timestamp": 1700000000},
    {"event": "ROLE_ASSIGNED", "user": "u2", "timestamp": 1700000100},
    {"event": "API_KEY_REVOKED", "user": "u1", "timestamp": 1700000200}
  ],
  "filter": {"user": "u1"}
}
print("----Part2----")
print(log_parser.filter_logs(data))       
                
        
        