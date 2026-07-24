"""Re-export legacy del cache persistente para compatibilidad."""

from trendscope.core.persistent_cache import PersistentCache, cache

get = cache.get
set = cache.set
clear = cache.clear
stats = cache.stats
