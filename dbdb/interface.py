import os
from dbdb.binary_tree import BinaryTree
from dbdb.physical import Storage


class DBDB:
    def __init__(self, f):
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self):
        if self._storage.closed:
            raise ValueError("Database is closed")

    def close(self):
        self._storage.close()

    def commit(self):
        self._assert_not_closed()
        self._tree.commit()

    def __getitem__(self, key):
        self._assert_not_closed()
        return self._tree.get(key)

    def __setitem__(self, key, value):
        self._assert_not_closed()
        return self._tree.set(key, value)

    def __delitem__(self, key):
        self._assert_not_closed()
        return self._tree.pop(key)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __len__(self):
        return len(self._tree)

    def __iter__(self):
        self._assert_not_closed()
        for key, _ in self._tree.items():
            yield key

    def keys(self):
        return list(self)

    def values(self):
        self._assert_not_closed()
        return [value for _, value in self._tree.items()]

    def items(self):
        self._assert_not_closed()
        return list(self._tree.items())

    def compact(self):
        """
        Cleans up disk space by copying only the live, committed nodes to a new file,
        replacing the old bloated file entirely.
        """
        self._assert_not_closed()
        
        current_path = self._storage._f.name
        compact_path = current_path + ".compact"

        # 1. Create a fresh temporary database
        new_db = connect(compact_path)

        # 2. Iterate through live items and write to the new DB
        for key, value in self._tree.items():
            new_db[key] = value
        
        new_db.commit()
        new_db.close()

        # 3. Safely close current storage to release OS file locks (Crucial for Windows)
        self.close()

        # 4. Atomically swap files (replace the bloated file with the fresh one)
        os.replace(compact_path, current_path)

        # 5. Reconnect current instance to the newly compacted file
        f = open(current_path, "r+b")
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)


def connect(dbname):
    try:
        f = open(dbname, "r+b")
    except IOError:
        f = open(dbname, "w+b")
    return DBDB(f)