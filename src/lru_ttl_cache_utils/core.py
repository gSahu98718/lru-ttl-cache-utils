"""A least-recently-used cache where entries also expire on a clock.

The cache combines two eviction policies:

* LRU — when the number of live entries exceeds ``maxsize``, the least
  recently *accessed* entry (via ``get`` or ``put``) is evicted.
* TTL — each entry carries an expiry time; an entry whose expiry has
  passed is treated as absent on the next access and is lazily removed.

Time is obtained from a caller-supplied ``clock`` callable, which must
return a comparable numeric value (typically seconds since some epoch).
Injecting the clock makes the cache deterministic in tests; you can pass a
fake clock and advance it by exact amounts instead of sleeping.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Hashable, Optional, TypeVar


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUTTLCache:
    """Bounded LRU cache with per-entry time-to-live.

    Parameters
    ----------
    maxsize:
        Upper bound on the number of entries stored. Once this many live
        entries are present, the least recently used entry is evicted
        before a new one is inserted. ``maxsize`` of 0 disables caching;
        every ``put`` is a no-op and every ``get`` returns ``None``.
    default_ttl:
        Default time-to-live applied to entries that do not specify an
        explicit ``ttl`` on ``put``. Expressed in the same units as the
        clock's return value. A ``default_ttl`` of ``None`` means entries
        live until evicted by LRU pressure.
    clock:
        Zero-argument callable returning a comparable numeric value.
        Defaults to ``time.monotonic``. Injecting a fake clock is the
        supported way to make time-dependent behaviour deterministic.
    """

    def __init__(
        self,
        maxsize: int,
        default_ttl: Optional[float] = None,
        clock: Callable[[], float] = None,
    ) -> None:
        if maxsize < 0:
            raise ValueError("maxsize must be non-negative")
        if default_ttl is not None and default_ttl <= 0:
            raise ValueError("default_ttl must be positive or None")
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        # ``OrderedDict`` gives O(1) move-to-end and popitem; we treat the
        # tail as least-recently-used. Using stdlib avoids third-party deps.
        self._data: "OrderedDict[object, tuple[float, object]]" = OrderedDict()
        if clock is None:
            import time
            self._clock: Callable[[], float] = time.monotonic
        else:
            self._clock = clock

    def _now(self) -> float:
        return self._clock()

    def _is_expired(self, expiry: Optional[float], now: float) -> bool:
        return expiry is not None and now >= expiry

    def get(self, key: object, default: object = None) -> object:
        """Return the value for ``key`` or ``default`` if absent/expired.

        A hit moves the entry to the most-recently-used position. A hit on
        an expired entry evicts it and returns ``default``.
        """
        if self._maxsize == 0:
            return default
        if key not in self._data:
            return default
        expiry, _value = self._data[key]
        now = self._now()
        if self._is_expired(expiry, now):
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return self._data[key][1]

    def put(
        self,
        key: object,
        value: object,
        ttl: Optional[float] = None,
    ) -> None:
        """Insert or overwrite ``key`` with ``value``.

        ``ttl`` overrides ``default_ttl`` for this entry. A ``ttl`` of
        ``None`` (and a ``default_ttl`` of ``None``) means the entry never
        expires on the clock; it can still be evicted under LRU pressure.
        """
        if self._maxsize == 0:
            return
        effective_ttl = ttl if ttl is not None else self._default_ttl
        if effective_ttl is not None and effective_ttl <= 0:
            raise ValueError("ttl must be positive or None")
        now = self._now()
        expiry = now + effective_ttl if effective_ttl is not None else None
        if key in self._data:
            self._data[key] = (expiry, value)
            self._data.move_to_end(key)
            return
        if len(self._data) >= self._maxsize:
            self._data.popitem(last=False)
        self._data[key] = (expiry, value)

    def __len__(self) -> int:
        # ``len`` reflects only unexpired entries at this instant, so callers
        # can rely on it for capacity checks without thinking about TTL.
        now = self._now()
        expired = [
            k for k, (expiry, _v) in self._data.items()
            if self._is_expired(expiry, now)
        ]
        for k in expired:
            del self._data[k]
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        if self._maxsize == 0:
            return False
        if key not in self._data:
            return False
        expiry, _value = self._data[key]
        if self._is_expired(expiry, self._now()):
            del self._data[key]
            return False
        return True

    def clear(self) -> None:
        """Remove every entry regardless of expiry."""
        self._data.clear()
