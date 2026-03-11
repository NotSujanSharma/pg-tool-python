"""Browse Tables tab — splitter layout with TableListPanel + DetailPanel."""

from PyQt5.QtWidgets import QVBoxLayout, QSplitter
from PyQt5.QtCore import Qt

from pgbrowser.tabs import BaseTab
from .table_list import TableListPanel
from .detail import DetailPanel


class BrowseTab(BaseTab):
    """The primary schema-browsing tab."""

    TAB_LABEL = "Browse Tables"

    def __init__(self, conn, params: dict, get_schema, parent=None):
        super().__init__(conn, params, get_schema, parent)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        self.table_list = TableListPanel(self.conn)
        self.table_list.setMinimumWidth(180)
        self.table_list.setMaximumWidth(340)
        self.table_list.table_selected.connect(self._on_table_selected)
        splitter.addWidget(self.table_list)

        self.detail = DetailPanel(self.conn)
        splitter.addWidget(self.detail)
        splitter.setSizes([240, 960])

        root.addWidget(splitter)

    # ── BaseTab hooks ──────────────────────────────────────────────────────────

    def on_schema_changed(self, schema: str) -> None:
        self.table_list.reload(schema)
        self.detail.clear()

    # ── Internal slots ─────────────────────────────────────────────────────────

    def _on_table_selected(self, name: str, ttype: str) -> None:
        self.detail.load(self.get_schema(), name, ttype)
