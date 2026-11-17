"""DBDB — database kunci/nilai persisten, dibangun ulang dari bab
*DBDB: Dog Bed Database* (Taavi Burns, 500 Lines or Less).

Tiga lapisan: fisik (physical.Storage), logis (logical.LogicalBase),
dan pohon biner immutable (binary_tree.BinaryTree), disajikan lewat
interface.DBDB. Fungsi connect() tinggal di interface dan diekspor
di sini pada Irisan 3.
"""

from .interface import DBDB, connect

__all__ = ['DBDB', 'connect']
