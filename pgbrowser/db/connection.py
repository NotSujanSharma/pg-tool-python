"""
Low-level database utilities.

exec_query  — run a parameterised query on an existing connection and return
              a list of RealDictRow objects (dict-like, key = column name).
              Must only be called from the main thread; background workers
              must open their own psycopg2 connection.

ConnectWorker — QThread that opens a new connection and emits success/failure.
"""

from PyQt5.QtCore import QThread, pyqtSignal

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None       # type: ignore[assignment]
    RealDictCursor = None  # type: ignore[assignment,misc]
    HAS_PSYCOPG2 = False


def exec_query(conn, query: str, params: tuple = ()) -> list:
    """Execute *query* with *params* on *conn* and return all rows.

    Rolls back the connection on any exception so it remains usable.
    """
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        return cur.fetchall()
    except Exception as exc:
        conn.rollback()
        raise exc


class ConnectWorker(QThread):
    """Opens a psycopg2 connection in a background thread."""

    success = pyqtSignal(object, dict)   # (conn, params)
    failure = pyqtSignal(str)            # error message

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self) -> None:
        try:
            conn = psycopg2.connect(
                host=self.params["host"],
                port=int(self.params["port"]),
                dbname=self.params["database"],
                user=self.params["user"],
                password=self.params["password"],
                connect_timeout=10,
                application_name="pgbrowser",
            )
            self.success.emit(conn, self.params)
        except Exception as exc:
            self.failure.emit(str(exc))
