# uji_irisan2.py — Bukti Irisan 2: pohon biner immutable.
# Wasitnya dict Python sendiri lewat operasi acak, ditambah dua
# bukti khas struktur immutable: akar lama tetap sah selamanya,
# dan satu sisipan hanya menulis segelintir simpul baru.

import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree, BinaryNodeRef

gagal = []


def cek(nama, kondisi, detail=''):
    print(('PASS' if kondisi else 'FAIL'), nama, detail)
    if not kondisi:
        gagal.append(nama)


def pohon_baru(path):
    f = open(path, 'r+b') if os.path.exists(path) else open(path, 'w+b')
    return BinaryTree(Storage(f))


with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, 'pohon.db')
    tree = pohon_baru(path)

    # --- dasar + persistensi ---
    tree.set('anjing', 'kasur empuk')
    tree.set('kucing', 'menara garuk')
    tree.commit()
    tree2 = pohon_baru(path)
    cek('buka ulang: nilai bertahan', tree2.get('anjing') == 'kasur empuk'
        and tree2.get('kucing') == 'menara garuk' and len(tree2) == 2)

    # --- diferensial vs dict ---
    random.seed(20261118)
    model = {'anjing': 'kasur empuk', 'kucing': 'menara garuk'}
    kunci_semesta = [f'k{i:02d}' for i in range(40)]
    tree = tree2
    cocok = True
    for langkah in range(600):
        k = random.choice(kunci_semesta)
        aksi = random.random()
        if aksi < 0.55:
            v = f'v{langkah}'
            tree.set(k, v)
            model[k] = v
        elif aksi < 0.8:
            if k in model:
                tree.delete(k)
                del model[k]
            else:
                try:
                    tree.delete(k)
                    cocok = False
                except KeyError:
                    pass
        else:
            try:
                dapat = tree.get(k)
                if model.get(k) != dapat:
                    cocok = False
            except KeyError:
                if k in model:
                    cocok = False
        if langkah % 50 == 49:
            tree.commit()
    tree.commit()
    isi_db = {}
    for k in kunci_semesta + ['anjing', 'kucing']:
        try:
            isi_db[k] = tree.get(k)
        except KeyError:
            pass
    cek('diferensial 600 operasi acak vs dict: isi identik',
        cocok and isi_db == model and len(tree) == len(model),
        f'{len(model)} kunci akhir')

    # --- akar lama adalah snapshot abadi ---
    tree.set('penanda', 'generasi-1')
    tree.commit()
    akar_lama = tree._storage.get_root_address()
    tree.set('penanda', 'generasi-2')
    tree.set('baru', 'hanya-di-gen2')
    tree.commit()
    snap = BinaryTree(tree._storage)
    nilai_lama = snap._get(snap._follow(BinaryNodeRef(address=akar_lama)), 'penanda')
    try:
        snap._get(snap._follow(BinaryNodeRef(address=akar_lama)), 'baru')
        bocor = True
    except KeyError:
        bocor = False
    cek('snapshot akar lama: nilai lama terbaca, kunci baru tak terlihat',
        nilai_lama == 'generasi-1' and not bocor)
    cek('akar kini melihat generasi baru', tree.get('penanda') == 'generasi-2')

    # --- berbagi struktur: satu sisipan menulis sedikit ---
    path2 = os.path.join(d, 'besar.db')
    besar = pohon_baru(path2)
    keys = [f'kunci-{i:04d}' for i in range(1000)]
    random.Random(7).shuffle(keys)
    for k in keys:
        besar.set(k, 'x' * 20)
    besar.commit()
    ukuran_penuh = os.path.getsize(path2)
    besar.set('kunci-1001', 'y' * 20)
    besar.commit()
    tumbuh = os.path.getsize(path2) - ukuran_penuh
    cek('sisip 1 kunci ke pohon 1000: berkas tumbuh < 2% ukuran penuh',
        tumbuh < ukuran_penuh * 0.02,
        f'tumbuh {tumbuh} B dari {ukuran_penuh} B')

    # --- belum commit = tak terlihat koneksi lain ---
    path3 = os.path.join(d, 'privat.db')
    a = pohon_baru(path3)
    a.set('rahasia', 'belum-commit')
    b = pohon_baru(path3)
    try:
        b.get('rahasia')
        terlihat = True
    except KeyError:
        terlihat = False
    cek('perubahan belum commit tidak terlihat pohon lain', not terlihat)
    a.commit()
    cek('sesudah commit, pohon lain melihatnya', b.get('rahasia') == 'belum-commit')

print()
if gagal:
    print('GAGAL:', ', '.join(gagal))
    sys.exit(1)
print('SEMUA PASS — Irisan 2 terbukti: immutable, diferensial bersih, snapshot abadi.')
