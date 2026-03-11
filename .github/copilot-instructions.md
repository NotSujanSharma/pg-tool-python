# PG Browser — GitHub Copilot Instructions

> These instructions give Copilot context about the project architecture,
> conventions, and patterns so it can generate consistent, maintainable code.

---

## Project overview

**PG Browser** is a desktop PostgreSQL schema explorer built with **PyQt5**.
It connects to a PostgreSQL database, lets the user browse tables/views, and
generates Excel data dictionaries.  The codebase targets Python ≥ 3.12.

---

## Package layout

```
pgbrowser/              ← main package
├── __init__.py
├── app.py              ← AppShell (QMainWindow) + main()
├── theme.py            ← STYLESHEET string + COLORS dict (Catppuccin Mocha)
├── config/
│   └── profiles.py     ← load/save connection profiles to ~/.config/pgbrowser/
├── db/
│   ├── connection.py   ← ConnectWorker (QThread) + exec_query() helper
│   └── queries.py      ← ALL SQL queries as plain functions
├── workers/
│   └── dict_export.py  ← DictExportWorker (QThread, opens its own conn)
├── views/
│   ├── login.py        ← LoginWidget
│   └── browser.py      ← BrowserWindow + _TAB_REGISTRY
└── tabs/
    ├── __init__.py     ← BaseTab (abstract base class)
    ├── browse/
    │   ├── tab.py          ← BrowseTab
    │   ├── table_list.py   ← TableListPanel (left panel)
    │   └── detail.py       ← DetailPanel (right panel, sub-tabs)
    └── data_dict/
        └── tab.py          ← DataDictTab

main.py                 ← thin entry point: `from pgbrowser.app import main`
```

---

## How to add a new tab

1. **Create a folder** `pgbrowser/tabs/your_feature/`
2. Add an empty `__init__.py`
3. Create `tab.py` with a class inheriting `BaseTab`:

```python
from pgbrowser.tabs import BaseTab

class YourFeatureTab(BaseTab):
    TAB_LABEL = "Your Feature"          # text shown on the tab

    def __init__(self, conn, params, get_schema, parent=None):
        super().__init__(conn, params, get_schema, parent)
        self._build_ui()

    def _build_ui(self):
        ...                             # build your QLayout here

    def on_schema_changed(self, schema: str):
        ...                             # react to schema selector changes

    def on_disconnected(self):
        ...                             # cancel any running workers
```

4. **Register it** in `pgbrowser/views/browser.py`:

```python
from pgbrowser.tabs.your_feature.tab import YourFeatureTab

_TAB_REGISTRY = [
    BrowseTab,
    DataDictTab,
    YourFeatureTab,   # ← add here
]
```

That's it — no other changes needed.

---

## How to add a new SQL query

All SQL lives in **`pgbrowser/db/queries.py`**.

```python
def get_something(conn, schema: str, table: str) -> list:
    return exec_query(conn, """
        SELECT ...
        FROM   ...
        WHERE  table_schema = %s AND table_name = %s
    """, (schema, table))
```

- Always use `exec_query(conn, sql, params)` — it handles rollback on error.
- Return `list` of `RealDictRow` (treat as `dict`).
- Use `%s` placeholders (psycopg2 style), **never** f-strings for SQL values.
- Put the function near related queries; keep the file grouped by topic.

Import the function where needed:
```python
from pgbrowser.db import queries
rows = queries.get_something(self.conn, schema, table)
```

---

## Threading rules

| Location | Thread | Connection |
|---|---|---|
| `BaseTab` subclasses, `DetailPanel`, `TableListPanel` | **Main thread** | Use shared `self.conn` |
| `QThread` workers (`DictExportWorker`, future workers) | **Worker thread** | Open a **new** `psycopg2.connect(...)` using `self.params` |

> **Never** pass the main-thread `conn` to a worker thread — psycopg2
> connections are not thread-safe.

Worker pattern:
```python
class MyWorker(QThread):
    finished = pyqtSignal(...)
    error    = pyqtSignal(str)

    def run(self):
        conn = psycopg2.connect(**...)
        try:
            ...
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            conn.close()
```

Always cancel/terminate running workers in `BaseTab.on_disconnected()`.

---

## Design system

All colours and the global Qt stylesheet live in **`pgbrowser/theme.py`**.

### Palette (Catppuccin Mocha)

| Token | Hex | Usage |
|---|---|---|
| `base` | `#1e1e2e` | Window background |
| `mantle` | `#181825` | Cards, top bar, list bg |
| `surface0` | `#313244` | Input bg, hover states |
| `surface1` | `#45475a` | Selected / pressed states |
| `blue` | `#89b4fa` | Primary accent, tab text |
| `green` | `#a6e3a1` | Success, nullable YES |
| `red` | `#f38ba8` | Errors, danger buttons |
| `yellow` | `#f9e2af` | PK highlights |
| `sky` | `#89dceb` | FK highlights |
| `subtext0` | `#a6adc8` | Secondary labels |

Use `COLORS["token"]` in Python when you need a hex value (e.g. `QColor`).

### Stylesheet conventions

- All styles go in `STYLESHEET` in `theme.py` — **never** inline `setStyleSheet`
  with arbitrary colours; use only palette hex values.
- Use `objectName` for variants: `QPushButton#secondary`, `QPushButton#danger`.
- Keep the stylesheet's section comments (`/* ── Topic ── */`) when adding new
  rules.

---

## Code conventions

- **Python ≥ 3.12** — use built-in generics (`list[str]`, `dict[str, int]`,
  `X | Y` unions) without `from __future__ import annotations`.
- Private methods and attributes use a single underscore prefix `_`.
- Qt signal handlers are named `_on_<event>` (e.g. `_on_schema_changed`).
- Prefer `pyqtSignal` for cross-widget communication over direct method calls.
- Do not add `try/except` inside DB query functions — let exceptions propagate
  so callers can decide how to handle them (exec_query already rolls back).
- Worker `run()` methods use a top-level `try/except Exception` and emit
  `error` signal — they must never crash silently.

---

## Running the app

```bash
# from the workspace root with the venv active
python main.py
```

Dependencies: `psycopg2-binary`, `PyQt5`, `openpyxl` (see `requirements.txt`).
