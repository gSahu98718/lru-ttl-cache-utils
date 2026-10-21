"""Deterministic tests for LRUTTLCache.

A fake clock advances in fixed increments; no wall-clock time is read.
"""

import math
import unittest

from lru_ttl_cache_utils import LRUTTLCache


class _FakeClock:
    def __init__(self, start=0.0):
        self._t = start

    def __call__(self):
        return self._t

    def advance(self, delta):
        self._t += delta


class TestLRUTTLCache(unittest.TestCase):
    def test_put_then_get(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=10, clock=clock)
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)

    def test_get_missing_returns_default(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=10, clock=clock)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")

    def test_get_expired_returns_default(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(5)
        self.assertIsNone(cache.get("a"))

    def test_get_not_yet_expired(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(4)
        self.assertEqual(cache.get("a"), 1)

    def test_lru_eviction_removes_least_recently_used(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=100, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_put_overwrite_keeps_position_recent(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=100, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 10)
        cache.put("c", 3)
        self.assertEqual(cache.get("a"), 10)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), 3)

    def test_per_entry_ttl_overrides_default(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=4, default_ttl=100, clock=clock)
        cache.put("short", 1, ttl=2)
        cache.put("long", 2, ttl=50)
        clock.advance(3)
        self.assertIsNone(cache.get("short"))
        self.assertEqual(cache.get("long"), 2)

    def test_ttl_none_means_never_expires(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=None, clock=clock)
        cache.put("a", 1)
        clock.advance(1000)
        self.assertEqual(cache.get("a"), 1)

    def test_maxsize_zero_disables_cache(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=0, default_ttl=10, clock=clock)
        cache.put("a", 1)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(len(cache), 0)
        self.assertNotIn("a", cache)

    def test_len_excludes_expired(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=4, default_ttl=5, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(len(cache), 2)
        clock.advance(5)
        self.assertEqual(len(cache), 0)

    def test_contains_handles_expiry(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(5)
        self.assertNotIn("a", cache)

    def test_clear_removes_all(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=4, default_ttl=100, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertIsNone(cache.get("a"))

    def test_negative_maxsize_raises(self):
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=-1)

    def test_non_positive_default_ttl_raises(self):
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=2, default_ttl=0)
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=2, default_ttl=-1)

    def test_non_positive_per_entry_ttl_raises(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=2, default_ttl=10, clock=clock)
        with self.assertRaises(ValueError):
            cache.put("a", 1, ttl=0)
        with self.assertRaises(ValueError):
            cache.put("a", 1, ttl=-1)

    def test_lru_pressure_after_expiry_frees_slot(self):
        clock = _FakeClock()
        cache = LRUTTLCache(maxsize=1, default_ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(5)
        cache.put("b", 2)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(len(cache), 1)


if __name__ == "__main__":
    unittest.main()
