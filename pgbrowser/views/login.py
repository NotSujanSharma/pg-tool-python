"""Login / connection screen."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QFrame, QSizePolicy, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from pgbrowser.config.profiles import load_profiles, save_profiles
from pgbrowser.db.connection import ConnectWorker


class LoginWidget(QWidget):
    """Connection form — emits connect_requested(conn, params) on success."""

    connect_requested = pyqtSignal(object, dict)

    def __init__(self):
        super().__init__()
        self.profiles: list = load_profiles()
        self._worker: ConnectWorker | None = None
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame(objectName="card")
        card.setFixedWidth(480)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(36, 32, 36, 32)
        cv.setSpacing(14)

        # Header
        title_lbl = QLabel("🐘  PG Browser")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #89b4fa; background: transparent;")
        cv.addWidget(title_lbl)

        sub_lbl = QLabel("PostgreSQL Schema Explorer")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        cv.addWidget(sub_lbl)

        cv.addSpacing(6)

        # Saved connections row
        pr_row = QHBoxLayout()
        pr_lbl = QLabel("Saved:")
        pr_lbl.setStyleSheet("background:transparent;")
        pr_row.addWidget(pr_lbl)
        self.profile_combo = QComboBox()
        self.profile_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.profile_combo.addItem("— New connection —")
        for p in self.profiles:
            self.profile_combo.addItem(self._profile_label(p))
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        pr_row.addWidget(self.profile_combo)
        cv.addLayout(pr_row)

        # Form fields
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.host_edit  = QLineEdit("localhost")
        self.port_edit  = QLineEdit("5432")
        self.db_edit    = QLineEdit()
        self.db_edit.setPlaceholderText("my_database")
        self.user_edit  = QLineEdit()
        self.user_edit.setPlaceholderText("postgres")
        self.pass_edit  = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setPlaceholderText("••••••••")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Optional name for this connection")

        form.addRow("Host:",     self.host_edit)
        form.addRow("Port:",     self.port_edit)
        form.addRow("Database:", self.db_edit)
        form.addRow("User:",     self.user_edit)
        form.addRow("Password:", self.pass_edit)
        form.addRow("Label:",    self.label_edit)
        cv.addLayout(form)

        self.save_check = QCheckBox("Remember this connection")
        cv.addWidget(self.save_check)

        cv.addSpacing(4)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.del_btn = QPushButton("Delete", objectName="danger")
        self.del_btn.setToolTip("Remove saved connection")
        self.del_btn.setVisible(False)
        self.del_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setDefault(True)
        self.connect_btn.clicked.connect(self._do_connect)
        btn_row.addWidget(self.connect_btn)
        cv.addLayout(btn_row)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet(
            "color: #f38ba8; font-size: 12px; background: transparent;"
        )
        cv.addWidget(self.status_lbl)

        root.addWidget(card, alignment=Qt.AlignCenter)
        self.pass_edit.returnPressed.connect(self._do_connect)

    # ── Profile helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _profile_label(p: dict) -> str:
        return p.get("name") or f"{p['user']}@{p['host']}/{p['database']}"

    def _on_profile_changed(self, idx: int) -> None:
        if idx == 0:
            self.host_edit.setText("localhost")
            self.port_edit.setText("5432")
            self.db_edit.clear()
            self.user_edit.clear()
            self.pass_edit.clear()
            self.label_edit.clear()
            self.del_btn.setVisible(False)
        else:
            p = self.profiles[idx - 1]
            self.host_edit.setText(p.get("host", "localhost"))
            self.port_edit.setText(str(p.get("port", 5432)))
            self.db_edit.setText(p.get("database", ""))
            self.user_edit.setText(p.get("user", ""))
            self.pass_edit.setText(p.get("password", ""))
            self.label_edit.setText(p.get("name", ""))
            self.del_btn.setVisible(True)

    def _delete_profile(self) -> None:
        idx = self.profile_combo.currentIndex()
        if idx == 0:
            return
        name = self.profile_combo.currentText()
        if (
            QMessageBox.question(
                self, "Delete Profile",
                f'Remove saved connection "{name}"?',
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.profiles.pop(idx - 1)
            save_profiles(self.profiles)
            self.profile_combo.removeItem(idx)
            self.profile_combo.setCurrentIndex(0)

    # ── Connect ────────────────────────────────────────────────────────────────

    def _do_connect(self) -> None:
        host     = self.host_edit.text().strip()
        port     = self.port_edit.text().strip()
        database = self.db_edit.text().strip()
        user     = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not all([host, port, database, user]):
            self.status_lbl.setText("Host, port, database and user are required.")
            return
        try:
            int(port)
        except ValueError:
            self.status_lbl.setText("Port must be a number.")
            return

        params = {
            "host": host, "port": port,
            "database": database, "user": user, "password": password,
            "name": self.label_edit.text().strip(),
        }
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting…")
        self.status_lbl.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: transparent;"
        )
        self.status_lbl.setText("Connecting…")

        self._worker = ConnectWorker(params)
        self._worker.success.connect(self._on_connected)
        self._worker.failure.connect(self._on_error)
        self._worker.start()

    def _on_connected(self, conn, params: dict) -> None:
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        self.status_lbl.setText("")

        if self.save_check.isChecked():
            label       = params.get("name") or self._profile_label(params)
            params["name"] = label
            cur_idx     = self.profile_combo.currentIndex()
            if cur_idx > 0:
                self.profiles[cur_idx - 1] = params
                self.profile_combo.setItemText(cur_idx, label)
            else:
                self.profiles.append(params)
                self.profile_combo.addItem(label)
            save_profiles(self.profiles)

        self.connect_requested.emit(conn, params)

    def _on_error(self, err: str) -> None:
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        self.status_lbl.setStyleSheet(
            "color: #f38ba8; font-size: 12px; background: transparent;"
        )
        self.status_lbl.setText(f"❌  {err}")
