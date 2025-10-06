

# 1) Identity & Rule Resolution (who + which limits exactly)

**Implement:**
`resolve_request_limits(request, config) -> {client_key, matched_rules[], effective_limit, effective_per_seconds, cost}`

**Input**

```json
{
  "request": {
    "method": "GET",
    "path": "/v1/search?q=cat",
    "ip": "203.0.113.7",
    "headers": {
      "Authorization": "Bearer eyJ...jwt...",
      "X-API-Key": "k_live_abc",
      "X-Forwarded-For": "198.51.100.9, 203.0.113.7"
    },
    "now_epoch": 1730812805
  },
  "config": {
    "identity_priority": ["user_id", "api_key", "ip"],
    "cidr_blocklist": ["10.0.0.0/8"],
    "endpoint_costs": {"/v1/search": 2, "/v1/upload": 5, "/v1/profile": 1, "/v1/users/:id": 1},
    "rules": [
      {"id":"ip_search_min","applies_to":"ip","endpoints":["/v1/search"],"limit":10,"per_seconds":60},
      {"id":"auth_user_hour","applies_to":"user","endpoints":["*"],"limit":1000,"per_seconds":3600},
      {"id":"premium_boost","applies_to":"user","endpoints":["*"],"limit_multiplier":10,"condition":"tier=='premium'"},
      {"id":"global_safety","applies_to":"global","endpoints":["*"],"limit":50000,"per_seconds":1}
    ],
    "jwt_claims": {"sub":"user_42","tier":"premium"}
  }
}
```

**Output (example)**

```json
{
  "client_key": "user:user_42|tier:premium",
  "matched_rules": ["auth_user_hour", "premium_boost", "global_safety", "ip_search_min"],
  "effective_limit": 10,
  "effective_per_seconds": 60,
  "cost": 2
}
```

**Parts**

* **A:** Parse identity via priority, prefer first available; use first IP in `X-Forwarded-For` if present.
* **B:** Match all rules (support `*`, exact, and `:param` routes); compute effective limit = **most restrictive** after applying multipliers/conditions.
* **C:** Return **reasoning bundle** (why each rule matched, multiplier math) for audit logs (not sent to client).

---

# 2) Deterministic Token-Bucket Simulation (single node, variable cost)

**Implement:**
`simulate_requests(events, rate_config) -> decisions[]`

**Input**

```json
{
  "events": [
    {"client_key":"user:user_42|tier:premium","timestamp": 1730812800,"cost":2},
    {"client_key":"user:user_42|tier:premium","timestamp": 1730812801,"cost":2},
    {"client_key":"user:user_42|tier:premium","timestamp": 1730812859,"cost":5},
    {"client_key":"user:user_42|tier:premium","timestamp": 1730812860,"cost":5},
    {"client_key":"ip:198.51.100.9|ep:/v1/search","timestamp":1730812860,"cost":2}
  ],
  "rate_config": {
    "capacity": 10,
    "refill_per_sec": 1, 
    "start_tokens": 10
  }
}
```

**Output (example)**

```json
[
  {"allowed": true,  "remaining": 8, "reset_in": 2},
  {"allowed": true,  "remaining": 6, "reset_in": 4},
  {"allowed": true,  "remaining": 1, "reset_in": 9},
  {"allowed": false, "remaining": 1, "reset_in": 1},
  {"allowed": true,  "remaining": 8, "reset_in": 2}
]
```

**Parts**

* **A:** Implement integer-math refill (no float drift), cap at `capacity`, variable `cost`.
* **B:** Return `reset_in` = seconds until bucket has ≥ `cost` tokens again.
* **C:** Add idempotency: if an event repeats with same `(client_key, timestamp, request_id)` within 60s, replay same decision without re-consuming tokens.

---

# 3) Atomic Redis Check (simulate the Lua boundary)

**Implement:**
`atomic_check_and_consume(state, op) -> {allowed, remaining, reset_epoch, new_state}`

* `state`: in-memory dict standing in for Redis hash per key:
  `state["user:user_42|tier:premium"] = {"tokens":7,"last_refill":1730812850,"capacity":10,"refill_per_sec":1}`
* `op`: `{ "client_key": "...", "now": 1730812860, "cost": 2, "ttl": 3600 }`

**Behavior**

* Perform **refill + decision + consume + TTL set** atomically; if key absent, initialize with `capacity` and `last_refill=now`.
* Return `reset_epoch` for headers.

**Example**

```json
{
  "state": {
    "user:user_42|tier:premium":{"tokens":7,"last_refill":1730812850,"capacity":10,"refill_per_sec":1}
  },
  "op": {"client_key":"user:user_42|tier:premium","now":1730812860,"cost":5,"ttl":3600}
}
```

**Output**

```json
{
  "allowed": true,
  "remaining": 2,
  "reset_epoch": 1730812863,
  "new_state": {
    "user:user_42|tier:premium":{"tokens":2,"last_refill":1730812860,"capacity":10,"refill_per_sec":1,"ttl":3600}
  }
}
```

**Parts**

* **A:** Implement as a single function to mirror a Lua script’s atomicity (no reads outside).
* **B:** Support per-key overrides (`capacity`, `refill_per_sec`) if present in state.
* **C:** Add **variable cost by endpoint**: accept `op.endpoint_cost` that overrides `cost`.

---

# 4) Mixed-Limit Decision Composer (user AND ip AND endpoint)

**Implement:**
`final_decision(request, config, redis_state) -> {passes, headers, audit}`

**Input**

```json
{
  "request": {
    "path": "/v1/search",
    "headers": {"Authorization":"Bearer eyJ...","X-Forwarded-For":"198.51.100.9"},
    "ip": "203.0.113.7",
    "now_epoch": 1730812900
  },
  "config": {
    "endpoint_costs": {"/v1/search":2},
    "rules": [
      {"id":"user_hour","applies_to":"user","endpoints":["*"],"limit":1000,"per_seconds":3600},
      {"id":"ip_min","applies_to":"ip","endpoints":["/v1/search"],"limit":10,"per_seconds":60},
      {"id":"endpoint_global","applies_to":"endpoint","endpoints":["/v1/search"],"limit":5000,"per_seconds":60}
    ],
    "jwt_claims": {"sub":"user_007","tier":"standard"}
  },
  "redis_state": {
    "user:user_007|tier:standard":{"tokens":10,"last_refill":1730812890,"capacity":1000,"refill_per_sec":1000/3600},
    "ip:198.51.100.9|ep:/v1/search":{"tokens":1,"last_refill":1730812898,"capacity":10,"refill_per_sec":10/60},
    "ep:/v1/search":{"tokens":3000,"last_refill":1730812890,"capacity":5000,"refill_per_sec":5000/60}
  }
}
```

**Output (example)**

```json
{
  "passes": false,
  "headers": {
    "X-RateLimit-Limit": "10",
    "X-RateLimit-Remaining": "0",
    "X-RateLimit-Reset": "1730812900",
    "Retry-After": "1"
  },
  "audit": {
    "decisions": [
      {"scope":"user","rule":"user_hour","allowed":true,"remaining":998},
      {"scope":"ip","rule":"ip_min","allowed":false,"remaining":0,"reset_epoch":1730812900},
      {"scope":"endpoint","rule":"endpoint_global","allowed":true,"remaining":2998}
    ],
    "most_restrictive":"ip_min"
  }
}
```

**Parts**

* **A:** Compute three independent token checks (user/ip/endpoint); **deny if any denies**.
* **B:** Headers must reflect the **most restrictive** rule’s limit/remaining/reset.
* **C:** If one scope is missing (e.g., anonymous user), skip that scope cleanly.

---

# 5) Failure Modes & Circuit Breaker (fail-closed default)

**Implement:**
`guarded_check(op, mode, cb_config, redis_call) -> decision`

* `mode`: `"fail_closed"` or `"fail_open"`.
* `cb_config`: `{ "window_sec": 30, "error_threshold": 0.25, "cooldown_sec": 60 }`.

**Input**

```json
{
  "ops": [
    {"client_key":"user:1","now":1730813000,"cost":1},
    {"client_key":"user:1","now":1730813001,"cost":1},
    {"client_key":"user:1","now":1730813002,"cost":1},
    {"client_key":"user:1","now":1730813003,"cost":1}
  ],
  "redis_error_pattern": [false, true, true, false],
  "mode": "fail_closed",
  "cb_config": {"window_sec":30,"error_threshold":0.5,"cooldown_sec":10}
}
```

**Desired Behavior (example)**

```json
[
  {"allowed": true,  "mode_used": "normal"},
  {"allowed": false, "mode_used": "fail_closed"},
  {"allowed": false, "mode_used": "circuit_open"},
  {"allowed": false, "mode_used": "circuit_open"}
]
```

**Parts**

* **A:** If Redis call errors → follow mode (closed: 429, open: allow).
* **B:** Circuit breaker: when error ratio in last `window_sec` ≥ threshold, trip to **circuit_open** for `cooldown_sec` (treat as fail-closed).
* **C:** Emit structured events (`rate-limiter.circuit_opened`, counts, window) as return metadata.

---

# 6) Shard Routing & Rebalance Impact (jump consistent hash)

**Implement:**
`assign_shards(keys, num_shards) -> mapping` and `rebalance_delta(before, after)`

**Input**

```json
{
  "keys": [
    "user:user_1","user:user_2","user:user_3","ip:198.51.100.9|ep:/v1/search",
    "user:user_9999","key:k_prod_XYZ","user:user_hot"
  ],
  "num_shards_start": 4,
  "num_shards_end": 5
}
```

**Output (example)**

```json
{
  "start": {
    "0": ["user:user_1","user:user_hot"],
    "1": ["user:user_2"],
    "2": ["user:user_3","key:k_prod_XYZ"],
    "3": ["ip:198.51.100.9|ep:/v1/search","user:user_9999"]
  },
  "end": {
    "0": ["user:user_1"],
    "1": ["user:user_2","user:user_hot"],
    "2": ["user:user_3"],
    "3": ["ip:198.51.100.9|ep:/v1/search"],
    "4": ["key:k_prod_XYZ","user:user_9999"]
  },
  "moved_keys": {
    "count": 3,
    "which": ["user:user_hot","key:k_prod_XYZ","user:user_9999"]
  }
}
```

**Parts**

* **A:** Use **jump consistent hash** to assign shards; demonstrate distribution.
* **B:** Show **delta** (minimize moves) when adding a shard.
* **C:** Add “key-tagging” support: if key contains `{…}`, hash only inside braces (e.g., `rate:{user:user_1}`).

---

# 7) Multi-Region Drift Bound (latency vs. strictness)

**Implement:**
`multi_region_decide(events, policy) -> results[]`

**Policy**

```json
{
  "regions": ["us-west","eu-central"],
  "per_region_bucket": {"capacity": 100, "refill_per_sec": 1},
  "roaming_grace": {"cold_start_tokens_fraction": 0.25} 
}
```

**Input**

```json
{
  "events": [
    {"client_key":"user:user_7","region":"us-west","ts":1730813200,"cost":50},
    {"client_key":"user:user_7","region":"us-west","ts":1730813205,"cost":60},
    {"client_key":"user:user_7","region":"eu-central","ts":1730813210,"cost":30},
    {"client_key":"user:user_7","region":"eu-central","ts":1730813212,"cost":80}
  ]
}
```

**Output (example)**

```json
[
  {"region":"us-west","allowed": true,  "remaining": 50, "reset_in":50},
  {"region":"us-west","allowed": false, "remaining": 0,  "reset_in":10},
  {"region":"eu-central","allowed": true, "remaining": 25, "reset_in":25, "grace_used": true},
  {"region":"eu-central","allowed": false,"remaining": 0,  "reset_in":55}
]
```

**Parts**

* **A:** Maintain **independent buckets per region**; no cross-region sync.
* **B:** On region hop, initialize bucket if absent with `capacity * fraction` tokens (grace), then continue normal refill.
* **C:** Compute **drift bound** over the sequence (max extra tokens user effectively gets due to roaming). Return `drift_tokens`.

---


