"""Reusable table/view list panel.

Supports two selection modes:

  single  — single-click selection; emits ``item_selected(name, ttype)``
  multi   — checkboxes; exposes ``selected_names()`` and emits
            ``selection_changed(names)``

Usage
-----
panel = ObjectListPanel(conn, mode="single")
panel.reload(schema)          # fetch from DB and render

# Optionally let the user narrow the list by loading names from a file:
# The "Load from file" button in the toolbar handles that automatically.
"""

import csv
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QComboBox, QPushButton, QFileDialog, QToolButton,
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
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.conn       = conn
        self._mode      = mode
        self._all_items: list[tuple[str, str]] = []
        self._file_names: set[str] | None = None   # None = no file filter active
        self._schema: str = ""
        self._checked_names: set[str] = set() if mode == "multi" else None
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

        # Text search + Load-from-file button on same row
        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        search_row.setContentsMargins(0, 0, 0, 0)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Filter…")
        self.search_edit.textChanged.connect(self._on_filter_changed)
        search_row.addWidget(self.search_edit)

        self._file_btn = QToolButton()
        self._file_btn.setText("📂")
        self._file_btn.setToolTip(
            "Load table names from a .txt or .csv file.\n"
            "Only those tables will be shown."
        )
        self._file_btn.setFixedSize(28, 28)
        self._file_btn.clicked.connect(self._on_load_file)
        search_row.addWidget(self._file_btn)

        self._clear_file_btn = QToolButton()
        self._clear_file_btn.setText("✕")
        self._clear_file_btn.setToolTip("Clear file filter — show all")
        self._clear_file_btn.setFixedSize(24, 28)
        self._clear_file_btn.setVisible(False)
        self._clear_file_btn.clicked.connect(self._on_clear_file)
        search_row.addWidget(self._clear_file_btn)

        lv.addLayout(search_row)

        # File filter indicator
        self._file_lbl = QLabel("")
        self._file_lbl.setStyleSheet(
            "color: #89b4fa; font-size: 10px; background: transparent;"
        )
        self._file_lbl.setVisible(False)
        self._file_lbl.setWordWrap(True)
        lv.addWidget(self._file_lbl)

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

        # Object list — no alternating row colors (theme handles item bg)
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        if self._mode == "multi":
            self.list_widget.itemChanged.connect(self._on_item_changed)
            self.list_widget.itemClicked.connect(self._on_item_clicked)
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

    def clear(self) -> None:
        """Clear everything including the stored schema."""
        self._schema = ""
        self._all_items = []
        self._file_names = None
        if self._mode == "multi":
            self._checked_names.clear()
        self._file_lbl.setVisible(False)
        self._clear_file_btn.setVisible(False)
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
            if (tf == "ALL" or t == tf)
            and txt in n.lower()
            and (self._file_names is None or n in self._file_names)
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
                # Restore checked state from global set
                if name in self._checked_names:
                    item.setCheckState(Qt.Checked)
                else:
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

    def _on_load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load table list from file",
            "",
            "Text / CSV files (*.txt *.csv);;All files (*)",
        )
        if not path:
            return
        names = self._read_names_from_file(path)
        if names is None:
            return
        self._file_names = names
        fname = os.path.basename(path)
        self._file_lbl.setText(f"📄 {fname}  ({len(names)} names)")
        self._file_lbl.setVisible(True)
        self._clear_file_btn.setVisible(True)
        self._render(self._visible_items())

    def _on_clear_file(self) -> None:
        self._file_names = None
        self._file_lbl.setVisible(False)
        self._clear_file_btn.setVisible(False)
        self._render(self._visible_items())

    @staticmethod
    def _read_names_from_file(path: str) -> set[str] | None:
        """Parse a .txt (one name per line) or .csv (first column) file."""
        names: set[str] = set()
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                if path.lower().endswith(".csv"):
                    reader = csv.reader(fh)
                    for row in reader:
                        if row:
                            name = row[0].strip()
                            if name:
                                names.add(name)
                else:
                    for line in fh:
                        name = line.strip()
                        if name:
                            names.add(name)
        except OSError:
            return None
        return names

    def _select_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
            name = item.data(Qt.UserRole + 1)
            self._checked_names.add(name)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit(self.selected_names())

    def _deselect_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
            name = item.data(Qt.UserRole + 1)
            self._checked_names.discard(name)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit(self.selected_names())

    def _on_item_changed(self, item) -> None:
        name = item.data(Qt.UserRole + 1)
        if item.checkState() == Qt.Checked:
            self._checked_names.add(name)
        else:
            self._checked_names.discard(name)
        self.selection_changed.emit(self.selected_names())

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            return
        name  = current.data(Qt.UserRole + 1)
        ttype = current.data(Qt.UserRole)
        if name:
            self.item_selected.emit(name, ttype)

    def _on_item_clicked(self, item):
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)