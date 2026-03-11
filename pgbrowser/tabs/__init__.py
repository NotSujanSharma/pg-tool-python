"""
BaseTab — contract that every browser tab must satisfy.

To add a new tab:
  1. Create pgbrowser/tabs/your_tab/__init__.py  (empty)
  2. Create pgbrowser/tabs/your_tab/tab.py  with a class inheriting BaseTab
  3. Set TAB_LABEL = "Your Label"
  4. Register it in pgbrowser/views/browser.py  _TAB_REGISTRY list
"""

from typing import Callable
from PyQt5.QtWidgets import QWidget


class BaseTab(QWidget):
    """Abstract base for all main-window browser tabs.

    Constructor arguments
    ---------------------
    conn       : live psycopg2 connection (main-thread only)
    params     : connection parameter dict  (host, port, database, user,
                 password, name) — used by workers that open their own conn
    get_schema : zero-arg callable returning the currently selected schema str
    """

    TAB_LABEL: str = "Tab"

    def __init__(
        self,
        conn,
        params: dict,
        get_schema: Callable[[], str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn       = conn
        self.params     = params
        self.get_schema = get_schema

    # ── Lifecycle hooks (override as needed) ───────────────────────────────────

    def on_schema_changed(self, schema: str) -> None:
        """Called by BrowserWindow whenever the schema selector changes."""

    def on_disconnected(self) -> None:
        """Called by BrowserWindow just before the connection is closed.

        Use this to cancel any running background workers.
        """
