# tool.py — Antarmuka baris perintah DBDB.
#
#   python3 -m dbdb.tool <berkas-db> get <kunci>
#   python3 -m dbdb.tool <berkas-db> set <kunci> <nilai>
#   python3 -m dbdb.tool <berkas-db> delete <kunci>
#
# Kode keluar mengikuti bab panduannya, supaya skrip shell bisa
# membedakan jenis kegagalan tanpa membaca pesan:
#   0 OK · 1 argumen salah · 2 kata kerja tak dikenal · 3 kunci tak ada
# Setiap set/delete di tool ini langsung di-commit: satu perintah
# adalah satu transaksi.

import sys

from . import interface

OK = 0
BAD_ARGS = 1
BAD_VERB = 2
BAD_KEY = 3

PENGGUNAAN = 'penggunaan: tool <berkas-db> {get|set|delete} <kunci> [nilai]'


def main(argv):
    if len(argv) < 4:
        print(PENGGUNAAN, file=sys.stderr)
        return BAD_ARGS
    dbname, verb, key = argv[1], argv[2], argv[3]
    if verb not in ('get', 'set', 'delete'):
        print(f'kata kerja tak dikenal: {verb}', file=sys.stderr)
        return BAD_VERB
    if verb == 'set' and len(argv) != 5:
        print(PENGGUNAAN, file=sys.stderr)
        return BAD_ARGS
    if verb in ('get', 'delete') and len(argv) != 4:
        print(PENGGUNAAN, file=sys.stderr)
        return BAD_ARGS

    db = interface.connect(dbname)
    try:
        if verb == 'get':
            sys.stdout.write(db[key] + '\n')
        elif verb == 'set':
            db[key] = argv[4]
            db.commit()
        else:  # delete
            del db[key]
            db.commit()
    except KeyError:
        print(f'kunci tidak ada: {key}', file=sys.stderr)
        return BAD_KEY
    finally:
        db.close()
    return OK


if __name__ == '__main__':
    sys.exit(main(sys.argv))
