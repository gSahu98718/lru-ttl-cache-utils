# lru-ttl-cache-utils

A least-recently-used cache where each entry also expires after a caller-supplied time-to-live. Standard library only.

```python
from lru_ttl_cache_utils import LRUTTLCache

clock = lambda: 0.0
cache = LRUTTLCache(maxsize=128, default_ttl=30, clock=clock)
cache.put("key", "value")
print(cache.get("key"))       # "value"
print(len(cache))             # 1
cache.clear()
```

## Why this exists

When a cache must be bounded *and* entries must not outlive their freshness, you need two eviction policies working together: LRU to cap memory, and TTL to cap staleness. This library provides exactly that, with the clock injected as a constructor argument so time-dependent behaviour is deterministic in tests — no sleeping, no wall-clock comparisons.

The trade-off: expiry is lazy. An entry whose TTL has elapsed is removed only when it is touched by a subsequent `get`, `put`, `len`, or `contains` call. There is no background thread sweeping the table. This keeps the implementation dependency-free and the cost predictable, at the price of transiently retaining expired entries in memory until they are next accessed.

## Edge you will hit

`default_ttl` and per-entry `ttl` are measured in whatever units your `clock` returns; if you use the default `time.monotonic`, the units are seconds. An entry inserted at clock value `T` with `ttl=5` is considered expired once the clock reads `>= T + 5`. Note the inclusive boundary: a `ttl` of 5 means the entry is live at `T + 4.999` and gone at `T + 5`.

`maxsize` of 0 disables caching entirely: every `put` is a no-op and every `get` returns the default. This is the supported way to turn the cache off without changing call sites.
