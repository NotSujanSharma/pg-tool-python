"""Left-panel table/view list for the Browse tab.

``TableListPanel`` is a thin wrapper around the shared ``ObjectListPanel``
that keeps the original ``table_selected`` signal name for compatibility.
"""

from PyQt5.QtCore import pyqtSignal

from pgbrowser.tabs.shared.object_list import ObjectListPanel


class TableListPanel(ObjectListPanel):
    """Single-select table/view panel used by the Browse tab.

    Signals
    -------
    table_selected(name: str, ttype: str)
        Re-emits ``item_selected`` under the legacy signal name so that
        ``BrowseTab`` does not need to change its connection.
    """

    table_selected = pyqtSignal(str, str)

    def __init__(self, conn, parent=None):
        super().__init__(conn, mode="single", parent=parent)
        self.item_selected.connect(self.table_selected)

