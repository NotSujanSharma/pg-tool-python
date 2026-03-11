"""
Design tokens and global Qt stylesheet.

All colours come from the Catppuccin Mocha palette.
Import COLORS in Python code when you need a hex value programmatically
(e.g. QColor(COLORS["green"])).  Everything else is driven by the CSS.
"""

# ── Palette ───────────────────────────────────────────────────────────────────
COLORS = {
    # Base layers
    "crust":    "#11111b",
    "mantle":   "#181825",
    "base":     "#1e1e2e",
    # Surfaces (used for cards, inputs, hover states)
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    # Overlays / muted text
    "overlay0": "#6c7086",
    "overlay1": "#7f849c",
    "subtext0": "#a6adc8",
    "text":     "#cdd6f4",
    # Accent colours
    "blue":     "#89b4fa",
    "lavender": "#b4befe",
    "sapphire": "#74c7ec",
    "sky":      "#89dceb",
    "teal":     "#94e2d5",
    "green":    "#a6e3a1",
    "yellow":   "#f9e2af",
    "peach":    "#fab387",
    "red":      "#f38ba8",
    "maroon":   "#eba0ac",
    "mauve":    "#cba6f7",
    "flamingo": "#f2cdcd",
    "rosewater":"#f5e0dc",
}

# ── Global Qt stylesheet ──────────────────────────────────────────────────────
STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
    font-size: 13px;
}

/* ── Login card ── */
QFrame#card {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 12px;
}

/* ── Inputs ── */
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 7px 10px;
    color: #cdd6f4;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QLineEdit:disabled {
    color: #585b70;
}
QLineEdit[echoMode="2"] {
    lineedit-password-character: 9679;
}

QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 7px 10px;
    color: #cdd6f4;
    min-width: 120px;
}
QComboBox:focus { border-color: #89b4fa; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #45475a;
    color: #cdd6f4;
    outline: none;
}

/* ── Buttons ── */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    min-width: 80px;
}
QPushButton:hover   { background-color: #b4befe; }
QPushButton:pressed { background-color: #74c7ec; }
QPushButton:disabled { background-color: #45475a; color: #6c7086; }

QPushButton#secondary {
    background-color: #313244;
    color: #cdd6f4;
}
QPushButton#secondary:hover { background-color: #45475a; }

QPushButton#danger {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#danger:hover { background-color: #eba0ac; }

/* ── List ── */
QListWidget {
    background-color: #181825;
    border: none;
    outline: none;
    padding: 4px 2px;
    alternate-background-color: #1e1e2e;
}
QListWidget::item {
    padding: 7px 12px;
    border-radius: 5px;
    margin: 1px 2px;
}
QListWidget::item:hover    { background-color: #313244; }
QListWidget::item:selected {
    background-color: #45475a;
    color: #89b4fa;
    font-weight: 600;
}

/* ── Table ── */
QTableWidget {
    background-color: #181825;
    border: none;
    outline: none;
    gridline-color: #313244;
    alternate-background-color: #1e1e2e;
}
QTableWidget::item { padding: 5px 10px; }
QTableWidget::item:selected {
    background-color: #313244;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #1e1e2e;
    color: #89b4fa;
    font-weight: 700;
    padding: 7px 10px;
    border: none;
    border-bottom: 2px solid #313244;
    border-right: 1px solid #2a2a3e;
}
QHeaderView::section:last { border-right: none; }

/* ── Splitter ── */
QSplitter::handle            { background-color: #313244; }
QSplitter::handle:horizontal { width: 1px; }

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #313244;
    border-top: none;
    background: #1e1e2e;
}
QTabBar::tab {
    background: #181825;
    color: #a6adc8;
    padding: 8px 22px;
    border: 1px solid #313244;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1e1e2e;
    color: #89b4fa;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { background: #282838; }

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: transparent; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #45475a; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: transparent; height: 8px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #45475a; border-radius: 4px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #585b70; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ── Groupbox ── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px; padding: 0 4px;
    color: #89b4fa; font-weight: 700;
}

/* ── Checkbox ── */
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 4px; border: 1px solid #45475a; background: #313244;
}
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }

/* ── Progress bar ── */
QProgressBar {
    background-color: #313244;
    border-radius: 3px;
    border: none;
    height: 6px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}

/* ── Misc ── */
QMessageBox, QDialog { background-color: #1e1e2e; }
QToolTip {
    background-color: #313244; color: #cdd6f4;
    border: 1px solid #45475a; padding: 4px 8px; border-radius: 4px;
}
"""
