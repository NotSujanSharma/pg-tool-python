"""
BrowserWindow — main authenticated screen.

Architecture
------------
The window hosts a top bar (schema selector + disconnect) above a
QTabWidget whose tabs are driven by _TAB_REGISTRY.

Adding a new tab
----------------
1. Create your tab class (inheriting BaseTab) under pgbrowser/tabs/
2. Import it below
3. Append it to _TAB_REGISTRY — nothing else needed
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QComboBox, QPushButton, QTabWidget,
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from pgbrowser.db import queries
from pgbrowser.tabs.browse.tab import BrowseTab
from pgbrowser.tabs.data_dict.tab import DataDictTab

# ── Tab registry ───────────────────────────────────────────────────────────────
# To add a new tab: import its class and append it to this list.
_TAB_REGISTRY = [
    BrowseTab,
    DataDictTab,
]


class BrowserWindow(QWidget):
    """Main window shown after a successful database connection."""

    logout_requested = pyqtSignal()

    def __init__(self, conn, params: dict):
        super().__init__()
        self.conn   = conn
        self.params = params
        self._tabs: list = []
        self._build_ui()
        self._load_schemas()

    # ── Getters used by tabs ───────────────────────────────────────────────────

    def _get_schema(self) -> str:
        return self.schema_combo.currentText()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)

        for TabClass in _TAB_REGISTRY:
            tab = TabClass(
                conn=self.conn,
                params=self.params,
                get_schema=self._get_schema,
            )
            self._tab_widget.addTab(tab, TabClass.TAB_LABEL)
            self._tabs.append(tab)

        root.addWidget(self._tab_widget)

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setFixedHeight(54)
        topbar.setStyleSheet(
            "QFrame { background-color: #181825;"
            " border-bottom: 1px solid #313244; }"
        )
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(16, 0, 16, 0)
        tb.setSpacing(10)

        logo = QLabel("🐘  PG Browser")
        logo.setFont(QFont("Segoe UI", 13, QFont.Bold))
        logo.setStyleSheet("color: #89b4fa; background: transparent;")
        tb.addWidget(logo)

        tb.addWidget(self._vline())

        conn_info = QLabel(
            f"{self.params['user']}@{self.params['host']}:{self.params['port']}"
            f"  /  {self.params['database']}"
        )
        conn_info.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        tb.addWidget(conn_info)
        tb.addStretch()

        schema_lbl = QLabel("Schema:")
        schema_lbl.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        tb.addWidget(schema_lbl)

        self.schema_combo = QComboBox()
        self.schema_combo.setMinimumWidth(160)
        self.schema_combo.setFixedHeight(32)
        self.schema_combo.currentTextChanged.connect(self._on_schema_changed)
        tb.addWidget(self.schema_combo)

        tb.addWidget(self._vline())

        disc_btn = QPushButton("⏏  Disconnect", objectName="secondary")
        disc_btn.setFixedHeight(32)
        disc_btn.clicked.connect(self._disconnect)
        tb.addWidget(disc_btn)

        return topbar

    @staticmethod
    def _vline() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("QFrame { color: #45475a; background: #45475a; }")
        sep.setFixedWidth(1)
        return sep

    # ── Schema loading ─────────────────────────────────────────────────────────

    def _load_schemas(self) -> None:
        rows = queries.get_schemas(self.conn)
        self.schema_combo.blockSignals(True)
        self.schema_combo.clear()
        for row in rows:
            self.schema_combo.addItem(row["schema_name"])
        self.schema_combo.blockSignals(False)

        idx   = self.schema_combo.findText("public")
        start = idx if idx >= 0 else 0
        self.schema_combo.setCurrentIndex(start)
        # Manually trigger since we blocked signals
        self._on_schema_changed(self.schema_combo.currentText())

    def _on_schema_changed(self, schema: str) -> None:
        if not schema:
            return
        for tab in self._tabs:
            tab.on_schema_changed(schema)

    # ── Disconnect ─────────────────────────────────────────────────────────────

    def _disconnect(self) -> None:
        for tab in self._tabs:
            tab.on_disconnected()
        try:
            self.conn.close()
        except Exception:
            pass
        self.logout_requested.emit()
