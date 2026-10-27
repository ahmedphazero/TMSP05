"""Tiny SQLite store so we can detect duplicate claims. Swap for the real TMS lookup later."""
import sqlite3
from contextlib import closing


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path):
    with closing(_connect(path)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extin TEXT NOT NULL,
                category TEXT NOT NULL,
                period_from TEXT NOT NULL,
                period_to TEXT NOT NULL,
                amount TEXT NOT NULL,
                created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS submission_invoices (
                submission_id INTEGER NOT NULL REFERENCES submissions(id),
                extin TEXT NOT NULL,
                invoice_ref TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_inv ON submission_invoices(extin, invoice_ref);
            """
        )
        conn.commit()


def find_exact_duplicate(path, extin, period_from, period_to, amount, invoices):
    """Same taxpayer, period, amount and identical invoice set."""
    wanted = sorted(invoices)
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            "SELECT id FROM submissions WHERE extin=? AND period_from=? AND period_to=? AND amount=?",
            (extin, period_from, period_to, amount),
        ).fetchall()
        for row in rows:
            refs = sorted(
                r["invoice_ref"]
                for r in conn.execute(
                    "SELECT invoice_ref FROM submission_invoices WHERE submission_id=?", (row["id"],)
                )
            )
            if refs == wanted:
                return row["id"]
    return None


def find_reused_invoices(path, extin, invoices):
    """Invoice references this taxpayer already used in an earlier claim."""
    if not invoices:
        return []
    marks = ",".join("?" for _ in invoices)
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            f"SELECT DISTINCT invoice_ref FROM submission_invoices WHERE extin=? AND invoice_ref IN ({marks})",
            (extin, *invoices),
        ).fetchall()
    return [r["invoice_ref"] for r in rows]


def save_submission(path, extin, category, period_from, period_to, amount, invoices):
    with closing(_connect(path)) as conn:
        cur = conn.execute(
            "INSERT INTO submissions (extin, category, period_from, period_to, amount) VALUES (?,?,?,?,?)",
            (extin, category, period_from, period_to, amount),
        )
        sid = cur.lastrowid
        conn.executemany(
            "INSERT INTO submission_invoices (submission_id, extin, invoice_ref) VALUES (?,?,?)",
            [(sid, extin, ref) for ref in invoices],
        )
        conn.commit()
        return sid
