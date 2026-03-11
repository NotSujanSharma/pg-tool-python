"""Right-panel detail view for the Browse tab (Columns / Indexes / FK sub-tabs)."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from pgbrowser.db import queries


class DetailPanel(QWidget):
    """Shows column, index and foreign-key details for a selected table."""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        rv = QVBoxLayout(self)
        rv.setContentsMargins(4, 10, 10, 10)
        rv.setSpacing(6)

        self.title_lbl = QLabel("Select a table to inspect")
        self.title_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.title_lbl.setStyleSheet(
            "color: #585b70; background: transparent; padding: 2px 4px;"
        )
        rv.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet(
            "color: #6c7086; font-size: 12px; background: transparent;"
            "padding: 0 4px 4px;"
        )
        rv.addWidget(self.meta_lbl)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setDocumentMode(True)

        self.col_table = self._make_table(
            ["#", "Column", "Type", "Nullable", "Default", "Constraints"]
        )
        self.idx_table = self._make_table(
            ["Index Name", "Method", "Unique", "Primary", "Columns"]
        )
        self.fk_table = self._make_table(
            ["Constraint", "Column(s)", "References", "On Update", "On Delete"]
        )

        self.sub_tabs.addTab(self._wrap(self.col_table), "Columns")
        self.sub_tabs.addTab(self._wrap(self.idx_table), "Indexes")
        self.sub_tabs.addTab(self._wrap(self.fk_table),  "Foreign Keys")
        rv.addWidget(self.sub_tabs)

    # ── Public API ─────────────────────────────────────────────────────────────

    def load(self, schema: str, table: str, ttype: str) -> None:
        """Populate all sub-tabs for *schema*.*table*."""
        self.title_lbl.setText(f"  {schema}.{table}")
        self.title_lbl.setStyleSheet(
            "color: #cdd6f4; background: transparent; padding: 2px 4px;"
        )

        kind = "TABLE" if ttype == "BASE TABLE" else "VIEW"
        if ttype == "BASE TABLE":
            try:
                est  = queries.get_table_row_estimate(self.conn, schema, table)
                meta = f"{kind}   •   ~{est:,} rows (estimated)"
            except Exception:
                meta = kind
        else:
            meta = kind
        self.meta_lbl.setText(meta)

        self._load_columns(schema, table)
        self._load_indexes(schema, table)
        self._load_foreign_keys(schema, table)

    def clear(self) -> None:
        self.title_lbl.setText("Select a table to inspect")
        self.title_lbl.setStyleSheet(
            "color: #585b70; background: transparent; padding: 2px 4px;"
        )
        self.meta_lbl.setText("")
        for t in (self.col_table, self.idx_table, self.fk_table):
            t.setRowCount(0)

    # ── Data loaders ───────────────────────────────────────────────────────────

    def _load_columns(self, schema: str, table: str) -> None:
        rows = queries.get_columns(self.conn, schema, table)
        t    = self.col_table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            nullable    = row["is_nullable"] == "YES"
            default_val = row["column_default"] or ""
            constraints = row["constraints"] or ""
            vals = [
                str(row["ordinal_position"]),
                row["column_name"],
                row["display_type"],
                "YES" if nullable else "NO",
                default_val,
                constraints,
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 3:
                    item.setForeground(
                        QColor("#a6e3a1") if nullable else QColor("#f38ba8")
                    )
                elif c == 5 and "PK" in constraints:
                    item.setForeground(QColor("#f9e2af"))
                    item.setFont(QFont("", -1, QFont.Bold))
                elif c == 5 and "FK" in constraints:
                    item.setForeground(QColor("#89dceb"))
                t.setItem(r, c, item)
        t.resizeColumnsToContents()
        t.setColumnWidth(0, 40)
        if t.columnWidth(1) < 150: t.setColumnWidth(1, 150)
        if t.columnWidth(2) < 130: t.setColumnWidth(2, 130)

    def _load_indexes(self, schema: str, table: str) -> None:
        rows = queries.get_indexes(self.conn, schema, table)
        t    = self.idx_table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["index_name"],
                row["index_method"].upper(),
                "YES" if row["is_unique"]  else "NO",
                "YES" if row["is_primary"] else "NO",
                row["columns"],
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 2:
                    item.setForeground(
                        QColor("#a6e3a1") if row["is_unique"] else QColor("#6c7086")
                    )
                if c == 3 and row["is_primary"]:
                    item.setForeground(QColor("#f9e2af"))
                    item.setFont(QFont("", -1, QFont.Bold))
                t.setItem(r, c, item)
        t.resizeColumnsToContents()

    def _load_foreign_keys(self, schema: str, table: str) -> None:
        rows = queries.get_foreign_keys(self.conn, schema, table)
        t    = self.fk_table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            ref  = f"{row['ref_table']} ({row['ref_columns']})"
            vals = [
                row["constraint_name"],
                row["columns"],
                ref,
                row["update_rule"],
                row["delete_rule"],
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 2:
                    item.setForeground(QColor("#89dceb"))
                t.setItem(r, c, item)
        t.resizeColumnsToContents()

    # ── Qt helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _make_table(headers: list) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.setWordWrap(False)
        t.setShowGrid(False)
        return t

    @staticmethod
    def _wrap(widget: QWidget) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.addWidget(widget)
        return w
