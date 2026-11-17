# logical.py — Lapisan logis DBDB.
#
# Dua gagasan di sini menanggung seluruh lapisan:
#
# 1. ValueRef — penunjuk yang malas. Ia memegang nilai di memori
#    ATAU alamatnya di disk, dan hanya menyeberang di antara
#    keduanya bila diminta (get/store). Berkat kemalasan ini
#    database sebesar apa pun tidak perlu dimuat seluruhnya:
#    yang disentuh hanya jalur dari akar ke kunci yang dicari.
#
# 2. LogicalBase — tata cara umum get/set/delete/commit yang
#    sama untuk struktur data apa pun di atas Storage: segarkan
#    alamat akar sebelum membaca (bila tak terkunci), kunci
#    sebelum menulis, dan commit = simpan pohon lalu pindahkan
#    alamat akar. Struktur konkretnya (pohon biner) mengisi
#    _get/_insert/_delete.


class ValueRef:
    """Rujukan ke satu nilai: di memori (_referent) atau di disk
    (_address). Alamat 0 berarti 'belum ada' — alamat sah pertama
    adalah 8, sesudah superblock."""

    def __init__(self, referent=None, address=0):
        self._referent = referent
        self._address = address

    @property
    def address(self):
        return self._address

    def get(self, storage):
        """Ikuti rujukan ini: muat dari disk bila perlu."""
        if self._referent is None and self._address:
            self._referent = self.string_to_referent(storage.read(self._address))
        return self._referent

    def store(self, storage):
        """Tulis nilai ke disk bila ia baru (belum beralamat)."""
        if self._referent is not None and not self._address:
            self.prepare_to_store(storage)
            self._address = storage.write(self.referent_to_string(self._referent))

    def prepare_to_store(self, storage):
        pass

    @staticmethod
    def referent_to_string(referent):
        return referent.encode('utf-8')

    @staticmethod
    def string_to_referent(bytestring):
        return bytestring.decode('utf-8')


class LogicalBase:
    node_ref_class = None
    value_ref_class = ValueRef

    def __init__(self, storage):
        self._storage = storage
        self._tree_ref = None
        self._refresh_tree_ref()

    def _refresh_tree_ref(self):
        self._tree_ref = self.node_ref_class(
            address=self._storage.get_root_address())

    def _follow(self, ref):
        return ref.get(self._storage)

    def get(self, key):
        # Pembaca tidak pernah mengunci. Bila storage tidak sedang
        # kita kunci, segarkan dulu alamat akarnya: yang terbaca
        # adalah commit terakhir seseorang — utuh, tak pernah
        # separuh. Bila kita sendiri yang mengunci (sedang
        # menulis), bacaan melihat pekerjaan kita yang belum
        # commit, apa adanya.
        if not self._storage.locked:
            self._refresh_tree_ref()
        return self._get(self._follow(self._tree_ref), key)

    def set(self, key, value):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._insert(
            self._follow(self._tree_ref), key, self.value_ref_class(value))

    def delete(self, key):
        if self._storage.lock():
            self._refresh_tree_ref()
        self._tree_ref = self._delete(self._follow(self._tree_ref), key)

    def commit(self):
        self._tree_ref.store(self._storage)
        self._storage.commit_root_address(self._tree_ref.address)

    def __len__(self):
        if not self._storage.locked:
            self._refresh_tree_ref()
        root = self._follow(self._tree_ref)
        return root.length if root is not None else 0

    # Diisi struktur konkret:
    def _get(self, node, key):
        raise NotImplementedError

    def _insert(self, node, key, value_ref):
        raise NotImplementedError

    def _delete(self, node, key):
        raise NotImplementedError
