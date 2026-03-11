"""Reusable table/view list panel.

Supports two selection modes:

  single  — single-click selection; emits ``item_selected(name, ttype)``
  multi   — checkboxes; exposes ``selected_names()`` and emits
            ``selection_changed(names)``

Usage
-----
# auto-loading (Browse tab style):
panel = ObjectListPanel(conn, mode="single")
panel.reload(schema)          # fetch and render immediately

# manual-loading (DataDict tab style):
panel = ObjectListPanel(conn, mode="multi", show_load_btn=True)
panel.set_schema(schema)      # store schema; user presses Load to fetch
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QComboBox, QPushButton,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from pgbrowser.db import queries


# (display text, table_type filter value)
_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("Tables only",    "BASE TABLE"),
    ("Views only",     "VIEW"),
    ("Tables & Views", "ALL"),
]


class ObjectListPanel(QWidget):
    """Searchable, filterable, optionally multi-select list of DB objects.

    Signals
    -------
    item_selected(name: str, ttype: str)
        Fired in *single* mode when the user clicks an item.
    selection_changed(names: list[str])
        Fired in *multi* mode whenever the checked set changes.
    """

    item_selected    = pyqtSignal(str, str)
    selection_changed = pyqtSignal(list)

    def __init__(
        self,
        conn,
        *,
        mode: str = "single",
        show_load_btn: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn           = conn
        self._mode          = mode
        self._show_load_btn = show_load_btn
        self._all_items: list[tuple[str, str]] = []
        self._schema: str = ""
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lv = QVBoxLayout(self)
        lv.setContentsMargins(8, 10, 4, 8)
        lv.setSpacing(6)

        title = QLabel("Tables & Views")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet(
            "color: #a6adc8; background: transparent; padding: 2px 4px;"
        )
        lv.addWidget(title)

        # Type filter
        self._type_combo = QComboBox()
        for label, _ in _TYPE_OPTIONS:
            self._type_combo.addItem(label)
        # index 0 = "Tables only" by default
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        lv.addWidget(self._type_combo)

        # Text search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Filter…")
        self.search_edit.textChanged.connect(self._on_filter_changed)
        lv.addWidget(self.search_edit)

        # Select All / Deselect All (multi mode only)
        if self._mode == "multi":
            sel_row = QHBoxLayout()
            sel_row.setSpacing(4)
            sel_row.setContentsMargins(0, 0, 0, 0)

            sel_all = QPushButton("Select All", objectName="secondary")
            sel_all.setFixedHeight(26)
            sel_all.clicked.connect(self._select_all)
            sel_row.addWidget(sel_all)

            desel_all = QPushButton("Deselect All", objectName="secondary")
            desel_all.setFixedHeight(26)
            desel_all.clicked.connect(self._deselect_all)
            sel_row.addWidget(desel_all)

            sel_row.addStretch()
            lv.addLayout(sel_row)

        # Load button (shown when show_load_btn=True)
        if self._show_load_btn:
            self._load_btn = QPushButton("Load")
            self._load_btn.clicked.connect(self._on_load_clicked)
            lv.addWidget(self._load_btn)

        # Object list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        if self._mode == "multi":
            self.list_widget.itemChanged.connect(self._on_item_changed)
        else:
            self.list_widget.currentItemChanged.connect(self._on_current_changed)
        lv.addWidget(self.list_widget)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(
            "color: #585b70; font-size: 11px; background: transparent;"
        )
        lv.addWidget(self.count_lbl)

    # ── Public API ─────────────────────────────────────────────────────────────

    def reload(self, schema: str) -> None:
        """Fetch objects from the DB and repopulate the list immediately."""
        self._schema = schema
        self.search_edit.clear()
        rows = queries.get_tables(self.conn, schema)
        self._all_items = [(r["table_name"], r["table_type"]) for r in rows]
        self._render(self._visible_items())

    def set_schema(self, schema: str) -> None:
        """Store *schema* without fetching — user must press Load."""
        self._schema = schema
        self._all_items = []
        self.search_edit.clear()
        self.list_widget.clear()
        self.count_lbl.setText("")

    def clear(self) -> None:
        """Clear everything including the stored schema."""
        self._schema = ""
        self._all_items = []
        self.search_edit.clear()
        self.list_widget.clear()
        self.count_lbl.setText("")

    def selected_names(self) -> list[str]:
        """Return names of checked items (multi mode only)."""
        return [
            self.list_widget.item(i).data(Qt.UserRole + 1)
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.Checked
        ]

    # ── Internals ──────────────────────────────────────────────────────────────

    def _type_filter(self) -> str:
        return _TYPE_OPTIONS[self._type_combo.currentIndex()][1]

    def _visible_items(self) -> list[tuple[str, str]]:
        tf  = self._type_filter()
        txt = self.search_edit.text().lower()
        return [
            (n, t) for n, t in self._all_items
            if (tf == "ALL" or t == tf) and txt in n.lower()
        ]

    def _render(self, items: list[tuple[str, str]]) -> None:
        if self._mode == "multi":
            self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for name, ttype in items:
            icon = "▦ " if ttype == "BASE TABLE" else "◫ "
            item = QListWidgetItem(icon + name)
            item.setData(Qt.UserRole,     ttype)
            item.setData(Qt.UserRole + 1, name)
            item.setToolTip("TABLE" if ttype == "BASE TABLE" else "VIEW")
            if self._mode == "multi":
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        if self._mode == "multi":
            self.list_widget.blockSignals(False)
        n = len(items)
        self.count_lbl.setText(f"{n} object{'s' if n != 1 else ''}")

    def _on_type_changed(self) -> None:
        self._render(self._visible_items())

    def _on_filter_changed(self, _text: str) -> None:
        self._render(self._visible_items())

    def _on_load_clicked(self) -> None:
        if self._schema:
            self.reload(self._schema)

    def _select_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit(self.selected_names())

    def _deselect_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit(self.selected_names())

    def _on_item_changed(self, _item) -> None:
        self.selection_changed.emit(self.selected_names())

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            return
        name  = current.data(Qt.UserRole + 1)
        ttype = current.data(Qt.UserRole)
        if name:
            self.item_selected.emit(name, ttype)
