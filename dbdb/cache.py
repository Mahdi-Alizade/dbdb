from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int = 128):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")
        self.capacity = capacity
        self._cache = OrderedDict()

    def get(self, key):
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    def __contains__(self, key):
        return key in self._cache

    def __len__(self):
        return len(self._cache)