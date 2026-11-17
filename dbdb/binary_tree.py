# binary_tree.py — Pohon biner immutable di atas disk.
#
# Simpul tidak pernah berubah sesudah dibuat. Menyisipkan kunci
# berarti membangun simpul-simpul BARU hanya di sepanjang jalur
# dari akar ke titik sisip (path copying); seluruh subpohon di
# luar jalur dipakai bersama apa adanya dengan pohon lama. Maka:
#
# - Akar lama menunjuk pohon lama yang utuh, selamanya — snapshot
#   gratis, dan pembaca tak pernah melihat keadaan separuh jadi.
# - Satu commit hanya menulis O(tinggi pohon) simpul baru.
#
# Harga yang dibayar (diakui babnya sendiri): pohon ini TIDAK
# seimbang — urutan sisip yang buruk (mis. kunci terurut)
# merosotkannya menjadi daftar berantai. Database sungguhan
# memakai B-tree; di sini kesederhanaan adalah tujuannya.

import pickle

from .logical import LogicalBase, ValueRef


class BinaryNode:
    def __init__(self, left_ref, key, value_ref, right_ref, length):
        self.left_ref = left_ref
        self.key = key
        self.value_ref = value_ref
        self.right_ref = right_ref
        self.length = length

    @classmethod
    def from_node(cls, node, **tukar):
        """Salin simpul dengan sebagian bidang diganti — satu-
        satunya cara 'mengubah' simpul immutable."""
        bidang = {
            'left_ref': node.left_ref,
            'key': node.key,
            'value_ref': node.value_ref,
            'right_ref': node.right_ref,
            'length': node.length,
        }
        bidang.update(tukar)
        return cls(**bidang)

    def store_refs(self, storage):
        self.value_ref.store(storage)
        self.left_ref.store(storage)
        self.right_ref.store(storage)


class BinaryNodeRef(ValueRef):
    def prepare_to_store(self, storage):
        if self._referent:
            self._referent.store_refs(storage)

    @staticmethod
    def referent_to_string(referent):
        return pickle.dumps({
            'left': referent.left_ref.address,
            'key': referent.key,
            'value': referent.value_ref.address,
            'right': referent.right_ref.address,
            'length': referent.length,
        })

    @staticmethod
    def string_to_referent(bytestring):
        d = pickle.loads(bytestring)
        return BinaryNode(
            BinaryNodeRef(address=d['left']),
            d['key'],
            ValueRef(address=d['value']),
            BinaryNodeRef(address=d['right']),
            d['length'],
        )


class BinaryTree(LogicalBase):
    node_ref_class = BinaryNodeRef

    def _panjang(self, ref):
        node = self._follow(ref)
        return node.length if node is not None else 0

    def _get(self, node, key):
        while node is not None:
            if key < node.key:
                node = self._follow(node.left_ref)
            elif node.key < key:
                node = self._follow(node.right_ref)
            else:
                return self._follow(node.value_ref)
        raise KeyError(key)

    def _insert(self, node, key, value_ref):
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(), key, value_ref,
                self.node_ref_class(), 1)
        elif key < node.key:
            kiri = self._insert(self._follow(node.left_ref), key, value_ref)
            new_node = BinaryNode.from_node(
                node, left_ref=kiri,
                length=1 + self._panjang(kiri) + self._panjang(node.right_ref))
        elif node.key < key:
            kanan = self._insert(self._follow(node.right_ref), key, value_ref)
            new_node = BinaryNode.from_node(
                node, right_ref=kanan,
                length=1 + self._panjang(node.left_ref) + self._panjang(kanan))
        else:
            new_node = BinaryNode.from_node(node, value_ref=value_ref)
        return self.node_ref_class(referent=new_node)

    def _delete(self, node, key):
        if node is None:
            raise KeyError(key)
        if key < node.key:
            kiri = self._delete(self._follow(node.left_ref), key)
            return self.node_ref_class(referent=BinaryNode.from_node(
                node, left_ref=kiri,
                length=1 + self._panjang(kiri) + self._panjang(node.right_ref)))
        if node.key < key:
            kanan = self._delete(self._follow(node.right_ref), key)
            return self.node_ref_class(referent=BinaryNode.from_node(
                node, right_ref=kanan,
                length=1 + self._panjang(node.left_ref) + self._panjang(kanan)))
        # Kunci ditemukan di simpul ini.
        kiri, kanan = node.left_ref, node.right_ref
        if self._follow(kiri) is None:
            return kanan
        if self._follow(kanan) is None:
            return kiri
        # Dua anak: ambil penerus (terkecil di subpohon kanan),
        # letakkan kunci+nilainya di sini, hapus simpul penerus itu.
        penerus = self._follow(kanan)
        while self._follow(penerus.left_ref) is not None:
            penerus = self._follow(penerus.left_ref)
        kanan_baru = self._delete(self._follow(kanan), penerus.key)
        return self.node_ref_class(referent=BinaryNode(
            kiri, penerus.key, penerus.value_ref, kanan_baru,
            length=1 + self._panjang(kiri) + self._panjang(kanan_baru)))
