import bisect
import hashlib


class ConsistentHashRing:
    def __init__(self, nodes=None, replicas: int = 100):
        """
        :param nodes: List of node endpoints, e.g. [("127.0.0.1", 8881), ...]
        :param replicas: Number of virtual nodes per physical node
        """
        self.replicas = replicas
        self.ring = dict()  # hash_value -> node_tuple
        self.sorted_keys = []  # sorted hash values for binary search

        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)

    def add_node(self, node: tuple):
        """Adds a physical node by creating virtual nodes on the ring."""
        node_id = f"{node[0]}:{node[1]}"
        for i in range(self.replicas):
            vnode_key = f"{node_id}#vnode{i}"
            val = self._hash(vnode_key)
            self.ring[val] = node
            bisect.insort(self.sorted_keys, val)

    def remove_node(self, node: tuple):
        """Removes a physical node and its virtual nodes from the ring."""
        node_id = f"{node[0]}:{node[1]}"
        for i in range(self.replicas):
            vnode_key = f"{node_id}#vnode{i}"
            val = self._hash(vnode_key)
            if val in self.ring:
                del self.ring[val]
                idx = bisect.bisect_left(self.sorted_keys, val)
                if idx < len(self.sorted_keys) and self.sorted_keys[idx] == val:
                    self.sorted_keys.pop(idx)

    def get_node(self, key: str) -> tuple:
        """Returns the physical node responsible for the given key."""
        if not self.ring:
            return None
        val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, val)
        if idx == len(self.sorted_keys):
            idx = 0  # Wrap around the ring
        return self.ring[self.sorted_keys[idx]]