"""
Application shell (QMainWindow) and main() entry point.
"""

import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QMessageBox,
)
from PyQt5.QtCore import Qt

from pgbrowser.db.connection import HAS_PSYCOPG2
from pgbrowser.theme import STYLESHEET
from pgbrowser.views.login import LoginWidget
from pgbrowser.views.browser import BrowserWindow


class AppShell(QMainWindow):
    """Top-level window that stacks the login screen and browser."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PG Browser")
        self.resize(1280, 760)
        self.setMinimumSize(900, 550)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._login = LoginWidget()
        self._login.connect_requested.connect(self._on_connected)
        self._stack.addWidget(self._login)

        self._browser: BrowserWindow | None = None

        if not HAS_PSYCOPG2:
            QMessageBox.critical(
                self,
                "Missing dependency",
                "psycopg2 is not installed.\n\nRun:  pip install psycopg2-binary",
            )

    def _on_connected(self, conn, params: dict) -> None:
        if self._browser is not None:
            self._stack.removeWidget(self._browser)
            self._browser.deleteLater()

        self._browser = BrowserWindow(conn, params)
        self._browser.logout_requested.connect(self._on_logout)
        self._stack.addWidget(self._browser)
        self._stack.setCurrentWidget(self._browser)
        self.setWindowTitle(
            f"PG Browser — {params['user']}@{params['host']}/{params['database']}"
        )

    def _on_logout(self) -> None:
        self._stack.setCurrentWidget(self._login)
        self.setWindowTitle("PG Browser")


def main() -> None:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("PG Browser")
    app.setApplicationDisplayName("PG Browser")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = AppShell()
    window.show()
    sys.exit(app.exec_())
