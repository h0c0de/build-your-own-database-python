# Rencana — Build Your Own Database (DBDB, Python)

Panduan: Taavi Burns, *DBDB: Dog Bed Database* — bab dari
*500 Lines or Less* (Architecture of Open Source Applications),
http://aosabook.org/en/500L/dbdb-dog-bed-database.html
Daftar induk: build-your-own-x, bagian Database, entri Python.

## Yang dibangun

Database kunci/nilai persisten dengan tiga lapisan persis seperti
babnya — dan babnya sendiri menyajikan DBDB sebagai rancangan jadi
yang dibedah, jadi irisan di sini mengikuti lapisannya:

- `dbdb/physical.py` — lapisan fisik: `Storage`, berkas append-only,
  superblock berisi alamat akar.
- `dbdb/logical.py` — lapisan logis: `LogicalBase` + `ValueRef`.
- `dbdb/binary_tree.py` — pohon biner immutable di atas disk.
- `dbdb/interface.py` — `DBDB`, API ala dict + `connect()`.
- `dbdb/tool.py` — CLI `get`/`set`/`delete`.

## Adaptasi yang dicatat terbuka

- Babnya memakai pustaka pihak ketiga `portalocker` untuk kunci
  berkas; build ini murni stdlib — kuncinya `fcntl.flock`, semantik
  sama di Linux (LOCK_EX eksklusif, terlepas saat proses mati).
- Nilai di API adalah `str` (dikodekan UTF-8 oleh ValueRef), kunci
  juga `str` — sesuai pemakaian tool di babnya.

## Irisan

- [x] Irisan 1 — selesai & terverifikasi 18 Nov 2026 (lihat CATATAN.md). Lapisan fisik: Storage append-only; catatan
      berawalan panjang; superblock 8 byte memegang alamat akar;
      tulis-mengembalikan-alamat; fsync sebelum alamat akar
      diperbarui; kunci flock. Bukti: byte lama tidak pernah berubah
      (append-only dibuktikan dari isi berkas), alamat akar
      round-trip, buka-ulang persisten.
- [x] Irisan 2 — selesai & terverifikasi 18 Nov 2026 (lihat CATATAN.md). Lapisan logis + pohon biner: ValueRef/BinaryNodeRef;
      sisip/ambil/hapus immutable (path copying) — akar lama tetap
      sah selamanya. Bukti: diferensial vs `dict` (operasi acak
      termasuk hapus), bukti berbagi struktur (sisip menulis
      ~O(log n) simpul baru), snapshot akar lama mengembalikan
      nilai lama sesudah commit baru.
- [x] Irisan 3 — selesai & terverifikasi 18 Nov 2026 (lihat CATATAN.md). Antarmuka + tool: DBDB ala dict (get/set/del,
      commit, close, len), `connect()` tak pernah menimpa berkas;
      CLI dengan kode keluar babnya (OK/BAD_ARGS/BAD_VERB/BAD_KEY).
      Bukti: CLI ujung-ke-ujung antar-proses, perubahan belum
      commit tak terlihat koneksi lain.
- [x] Irisan 4 — selesai, baterai lulus & terbit 18 Nov 2026 (lihat CATATAN.md). Final: baterai durabilitas & konkurensi —
      penulis dibunuh -9 di tengah kerja → DB terbuka pada commit
      terakhir; pembaca tanpa kunci membaca snapshot konsisten
      selagi penulis commit beruntun (tak pernah melihat keadaan
      robek); baca-basi diperlihatkan sebagai semantik yang
      disengaja; tutup + terbit.

## Pagar selesai

- [x] `db[k]=v; db.commit()` bertahan melewati buka-ulang dan
      kematian proses, terverifikasi diferensial vs dict.
- [x] `CATATAN.md` satu halaman per irisan: konsep inti + temuan.
- [ ] Repo GitHub publik `build-your-own-database-python` terbit & terverifikasi.
