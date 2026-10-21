"""lru-ttl-cache-utils: a least-recently-used cache with per-entry time expiry.

Only the standard library is used.
"""

from .core import LRUTTLCache

__all__ = ["LRUTTLCache"]
