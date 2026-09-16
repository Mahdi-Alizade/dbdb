import sys
from dbdb.interface import connect


def usage():
    sys.stderr.write(
        "Usage: python -m dbdb.tool <dbfile> get <key>\n"
        "       python -m dbdb.tool <dbfile> set <key> <value>\n"
        "       python -m dbdb.tool <dbfile> delete <key>\n"
    )
    return 1


def main(argv):
    if len(argv) < 3:
        return usage()

    dbname = argv[1]
    verb = argv[2]

    db = connect(dbname)
    try:
        if verb == "get":
            if len(argv) != 4:
                return usage()
            try:
                sys.stdout.write(str(db[argv[3]]) + "\n")
                return 0
            except KeyError:
                sys.stderr.write(f"KeyError: Key '{argv[3]}' not found\n")
                return 1

        elif verb == "set":
            if len(argv) != 5:
                return usage()
            db[argv[3]] = argv[4]
            db.commit()
            return 0

        elif verb == "delete":
            if len(argv) != 4:
                return usage()
            try:
                del db[argv[3]]
                db.commit()
                return 0
            except KeyError:
                sys.stderr.write(f"KeyError: Key '{argv[3]}' not found\n")
                return 1

        else:
            return usage()
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))