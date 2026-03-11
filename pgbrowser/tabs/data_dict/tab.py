"""
Data Dictionary Generator tab.

Layout
------
Left  — ObjectListPanel (multi-select, auto-loads on schema change)
Right — top: Generate controls
        middle: scrollable output log
        bottom: Save As… button
"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton,
    QTextEdit, QProgressBar, QFrame,
    QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from pgbrowser.tabs import BaseTab
from pgbrowser.tabs.shared.object_list import ObjectListPanel
from pgbrowser.workers.dict_export import DictExportWorker


class DataDictTab(BaseTab):
    """Generate an Excel data dictionary for selected tables/views."""

    TAB_LABEL = "Data Dictionary"

    def __init__(self, conn, params: dict, get_schema, parent=None):
        super().__init__(conn, params, get_schema, parent)
        self._export_worker: DictExportWorker | None = None
        self._last_export_bytes: bytes | None = None
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        # ── Left: object list ──────────────────────────────────────────────────
        self._object_list = ObjectListPanel(
            self.conn,
            mode="multi",
        )
        self._object_list.setMinimumWidth(180)
        self._object_list.setMaximumWidth(340)
        self._object_list.selection_changed.connect(self._on_selection_changed)
        splitter.addWidget(self._object_list)

        # ── Right panel ────────────────────────────────────────────────────────
        right = QFrame()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(16, 16, 16, 14)
        rv.setSpacing(10)

        # Title
        title = QLabel("Data Dictionary Generator")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #cdd6f4; background: transparent;")
        rv.addWidget(title)

        subtitle = QLabel(
            "Select tables/views on the left, then click Generate to produce "
            "an Excel workbook with one sheet per table."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        rv.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("QFrame { color: #313244; background: #313244; }")
        sep.setFixedHeight(1)
        rv.addWidget(sep)

        # Generate controls row
        gen_row = QHBoxLayout()
        gen_row.setSpacing(10)

        self._sel_lbl = QLabel("0 selected")
        self._sel_lbl.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        gen_row.addWidget(self._sel_lbl)

        gen_row.addStretch()

        self._gen_btn = QPushButton("⬇  Generate")
        self._gen_btn.setFixedWidth(140)
        self._gen_btn.setEnabled(False)
        self._gen_btn.clicked.connect(self._generate)
        gen_row.addWidget(self._gen_btn)

        rv.addLayout(gen_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(5)
        self._progress.setTextVisible(False)
        rv.addWidget(self._progress)

        # Output log
        log_lbl = QLabel("Output")
        log_lbl.setStyleSheet(
            "color: #585b70; font-size: 11px; background: transparent;"
        )
        rv.addWidget(log_lbl)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText(
            "Generation output will appear here…"
        )
        self._output.setFont(QFont("Courier New", 10))
        self._output.setStyleSheet(
            "QTextEdit {"
            "  background: #181825;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "  border-radius: 6px;"
            "  padding: 6px;"
            "}"
        )
        rv.addWidget(self._output, stretch=1)

        # Save As… button row
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        save_row.addStretch()

        self._save_btn = QPushButton("💾  Save As…")
        self._save_btn.setFixedWidth(150)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_as)
        save_row.addWidget(self._save_btn)

        rv.addLayout(save_row)

        splitter.addWidget(right)
        splitter.setSizes([240, 960])

        root.addWidget(splitter)

    # ── BaseTab hooks ──────────────────────────────────────────────────────────

    def on_schema_changed(self, schema: str) -> None:
        self._reset_right_panel()
        if schema:
            self._object_list.reload(schema)
            self._log(f"Loaded objects for schema '{schema}'.", "#a6adc8")

    def on_disconnected(self) -> None:
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.terminate()
            self._export_worker.wait()

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_selection_changed(self, names: list[str]) -> None:
        n = len(names)
        self._sel_lbl.setText(f"{n} selected")
        self._gen_btn.setEnabled(n > 0)

    def _generate(self) -> None:
        selected = self._object_list.selected_names()
        if not selected:
            QMessageBox.warning(
                self,
                "No Items Selected",
                "Please select at least one table or view before generating.",
            )
            return

        schema = self.get_schema()
        if not schema:
            return

        self._gen_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._last_export_bytes = None
        self._progress.setRange(0, len(selected))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._output.clear()
        self._log(
            f"Starting generation for {len(selected)} object(s) in schema '{schema}'…",
            "#89b4fa",
        )

        self._export_worker = DictExportWorker(self.params, schema, selected)
        self._export_worker.progress.connect(self._on_progress)
        self._export_worker.finished.connect(self._on_finished)
        self._export_worker.error.connect(self._on_error)
        self._export_worker.start()

    def _on_progress(self, current: int, total: int, name: str) -> None:
        self._progress.setValue(current)
        self._log(f"  [{current}/{total}] Processing: {name}", "#a6adc8")

    def _on_finished(self, data: bytes) -> None:
        self._last_export_bytes = data
        self._gen_btn.setEnabled(len(self._object_list.selected_names()) > 0)
        self._progress.setVisible(False)
        self._save_btn.setEnabled(True)
        kb = len(data) // 1024
        self._log(f"✓  Done — {kb} KB generated. Click Save As… to write to disk.", "#a6e3a1")

    def _on_error(self, err: str) -> None:
        self._gen_btn.setEnabled(len(self._object_list.selected_names()) > 0)
        self._progress.setVisible(False)
        self._log(f"❌  {err}", "#f38ba8")

    def _save_as(self) -> None:
        if not self._last_export_bytes:
            return
        schema = self.get_schema() or "schema"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data Dictionary",
            f"data_dictionary_{schema}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"
        try:
            with open(path, "wb") as fh:
                fh.write(self._last_export_bytes)
            self._log(f"💾  Saved: {path}", "#a6e3a1")
        except OSError as exc:
            self._log(f"❌  Save failed: {exc}", "#f38ba8")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _log(self, msg: str, color: str = "#cdd6f4") -> None:
        self._output.append(f'<span style="color:{color};">{msg}</span>')

    def _reset_right_panel(self) -> None:
        self._output.clear()
        self._progress.setVisible(False)
        self._last_export_bytes = None
        self._gen_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._sel_lbl.setText("0 selected")
