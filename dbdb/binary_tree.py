import pickle


class ValueRef:
    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

    def prepare_to_store(self, storage):
        pass

    @staticmethod
    def referent_to_string(referent):
        return pickle.dumps(referent)

    @staticmethod
    def string_to_referent(string):
        return pickle.loads(string)

    def get(self, storage):
        if self._referent is None and self._address:
            self._referent = self.string_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage):
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))


class BinaryNodeRef(ValueRef):
    def prepare_to_store(self, storage):
        if self._referent:
            self._referent.store_refs(storage)

    @staticmethod
    def referent_to_string(referent):
        data = {
            "left": referent.left_ref.address,
            "right": referent.right_ref.address,
            "key": referent.key,
            "value": referent.value_ref.address,
            "length": referent.length,
        }
        return pickle.dumps(data)

    @staticmethod
    def string_to_referent(string):
        data = pickle.loads(string)
        return BinaryNode(
            BinaryNodeRef(address=data["left"]),
            BinaryNodeRef(address=data["right"]),
            data["key"],
            ValueRef(address=data["value"]),
            data["length"],
        )


class BinaryNode:
    def __init__(self, left_ref, right_ref, key, value_ref, length):
        self.left_ref = left_ref
        self.right_ref = right_ref
        self.key = key
        self.value_ref = value_ref
        self.length = length

    def store_refs(self, storage):
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)


class BinaryTree:
    node_ref_class = BinaryNodeRef

    def __init__(self, storage):
        self._storage = storage
        self._refresh_tree_ref()

    def commit(self):
        root_address = self._tree_ref.address
        self._tree_ref.store(self._storage)
        self._storage.commit_root_address(self._tree_ref.address)

    def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(
            address=self._storage.get_root_address()
        )

    def get(self, key):
        if not self._storage.locked:
            self._refresh_tree_ref()
        node = self._follow(self._tree_ref)
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif key > node.key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError(key)

    def set(self, key, value):
        if self._storage.lock():
            self._refresh_tree_ref()
        node = self._follow(self._tree_ref)
        new_node_ref = self._insert(node, key, ValueRef(value))
        self._tree_ref = new_node_ref

    def _insert(self, node, key, value_ref):
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(),
                self.node_ref_class(),
                key,
                value_ref,
                1,
            )
        elif key < node.key:
            new_left = self._insert(self._follow(node.left_ref), key, value_ref)
            new_node = BinaryNode(
                new_left,
                node.right_ref,
                node.key,
                node.value_ref,
                node.length + (1 if new_left.get(self._storage).length > self._get_length(node.left_ref) else 0),
            )
        elif key > node.key:
            new_right = self._insert(self._follow(node.right_ref), key, value_ref)
            new_node = BinaryNode(
                node.left_ref,
                new_right,
                node.key,
                node.value_ref,
                node.length + (1 if new_right.get(self._storage).length > self._get_length(node.right_ref) else 0),
            )
        else:
            new_node = BinaryNode(
                node.left_ref,
                node.right_ref,
                key,
                value_ref,
                node.length,
            )
        return self.node_ref_class(referent=new_node)

    def _get_length(self, node_ref):
        node = self._follow(node_ref)
        return node.length if node else 0

    def _follow(self, ref):
        return ref.get(self._storage) if ref else None

    def __len__(self):
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        return root.length if root else 0