# interface.py — Wajah DBDB bagi pemakainya.
#
# Kelas DBDB bertingkah seperti dict Python yang kebetulan
# tinggal di disk: db['kunci'] = 'nilai', db['kunci'], del
# db['kunci'], 'kunci' in db, len(db). Bedanya satu dan besar:
# tidak ada yang permanen sampai commit() dipanggil — persis
# seperti transaksi database sungguhan, diperkecil sampai tinggal
# intinya. connect() membuka berkas yang sudah ada TANPA pernah
# memotongnya (mode 'r+b'); berkas baru dibuat hanya bila belum
# ada.

import os

from .binary_tree import BinaryTree
from .physical import Storage


class DBDB:
    def __init__(self, f):
        self._storage = Storage(f)
        self._tree = BinaryTree(self._storage)

    def _assert_not_closed(self):
        if self._storage.closed:
            raise ValueError('Database sudah ditutup.')

    @staticmethod
    def _assert_str(x, apa):
        if not isinstance(x, str):
            raise TypeError(f'{apa} harus str, bukan {type(x).__name__}')

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
        self._assert_str(key, 'kunci')
        self._assert_str(value, 'nilai')
        return self._tree.set(key, value)

    def __delitem__(self, key):
        self._assert_not_closed()
        return self._tree.delete(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def __len__(self):
        self._assert_not_closed()
        return len(self._tree)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def connect(dbname):
    """Buka (atau buat) database di path dbname. Berkas yang
    sudah ada tidak pernah ditimpa atau dipotong."""
    try:
        f = open(dbname, 'r+b')
    except FileNotFoundError:
        fd = os.open(dbname, os.O_RDWR | os.O_CREAT)
        f = os.fdopen(fd, 'r+b')
    return DBDB(f)
