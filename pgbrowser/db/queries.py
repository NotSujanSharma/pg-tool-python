"""
All SQL query functions for PG Browser.

Every public function:
  • takes *conn* as its first argument (the shared main-thread connection)
  • delegates execution to exec_query() so rollback is handled uniformly
  • returns a list of dict-like RealDictRow objects

To add a new query:  just add a new function here, import it wherever needed,
and write a corresponding test in tests/db/test_queries.py (if you have them).
"""

from .connection import exec_query


# ── Schema / table discovery ──────────────────────────────────────────────────

def get_schemas(conn) -> list:
    """Return all user-visible schemas, with 'public' first."""
    return exec_query(conn, """
        SELECT schema_name
        FROM   information_schema.schemata
        WHERE  schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
          AND  schema_name NOT LIKE 'pg_temp_%%'
          AND  schema_name NOT LIKE 'pg_toast_temp_%%'
        ORDER BY
            CASE WHEN schema_name = 'public' THEN 0 ELSE 1 END,
            schema_name
    """)


def get_tables(conn, schema: str) -> list:
    """Return all tables and views in *schema*, views first then alpha."""
    return exec_query(conn, """
        SELECT table_name, table_type
        FROM   information_schema.tables
        WHERE  table_schema = %s
        ORDER BY table_type DESC, table_name
    """, (schema,))


# ── Table metadata ────────────────────────────────────────────────────────────

def get_table_row_estimate(conn, schema: str, table: str) -> int:
    """Return the planner's row-count estimate for *schema*.*table*."""
    rows = exec_query(conn, """
        SELECT reltuples::bigint AS estimate
        FROM   pg_class c
        JOIN   pg_namespace n ON n.oid = c.relnamespace
        WHERE  n.nspname = %s AND c.relname = %s
    """, (schema, table))
    return rows[0]["estimate"] if rows else 0


def get_columns(conn, schema: str, table: str) -> list:
    """Return column info for *schema*.*table* (for the Browse tab)."""
    return exec_query(conn, """
        SELECT
            c.ordinal_position,
            c.column_name,
            CASE
                WHEN c.character_maximum_length IS NOT NULL
                    THEN c.data_type || '(' || c.character_maximum_length || ')'
                WHEN c.numeric_precision IS NOT NULL
                     AND c.data_type IN ('numeric', 'decimal')
                    THEN c.data_type
                         || '(' || c.numeric_precision
                         || ',' || COALESCE(c.numeric_scale::text, '0') || ')'
                ELSE c.data_type
            END AS display_type,
            c.is_nullable,
            c.column_default,
            COALESCE(STRING_AGG(DISTINCT
                CASE tc.constraint_type
                    WHEN 'PRIMARY KEY' THEN 'PK'
                    WHEN 'FOREIGN KEY' THEN 'FK'
                    WHEN 'UNIQUE'      THEN 'UQ'
                    ELSE tc.constraint_type
                END,
                ', '), '') AS constraints
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON  c.table_schema = kcu.table_schema
            AND c.table_name   = kcu.table_name
            AND c.column_name  = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON  kcu.constraint_name   = tc.constraint_name
            AND kcu.constraint_schema = tc.constraint_schema
            AND kcu.table_name        = tc.table_name
        WHERE c.table_schema = %s AND c.table_name = %s
        GROUP BY c.ordinal_position, c.column_name, c.data_type,
                 c.character_maximum_length, c.numeric_precision,
                 c.numeric_scale, c.is_nullable, c.column_default
        ORDER BY c.ordinal_position
    """, (schema, table))


def get_indexes(conn, schema: str, table: str) -> list:
    """Return index info for *schema*.*table*."""
    return exec_query(conn, """
        SELECT
            pidx.indexname   AS index_name,
            UPPER(COALESCE(
                SUBSTRING(pidx.indexdef FROM ' USING (\\w+)'),
                'btree'
            ))               AS index_method,
            ix.indisunique   AS is_unique,
            ix.indisprimary  AS is_primary,
            ARRAY_TO_STRING(ARRAY(
                SELECT a.attname
                FROM   pg_attribute a
                WHERE  a.attrelid = ix.indrelid
                  AND  a.attnum   = ANY(ix.indkey)
                  AND  a.attnum  > 0
                ORDER BY array_position(ix.indkey, a.attnum::smallint)
            ), ', ') AS columns
        FROM   pg_indexes  pidx
        JOIN   pg_class    ic ON ic.relname = pidx.indexname
        JOIN   pg_namespace n  ON n.oid = ic.relnamespace
                              AND n.nspname = pidx.schemaname
        JOIN   pg_index    ix  ON ix.indexrelid = ic.oid
        WHERE  pidx.schemaname = %s AND pidx.tablename = %s
        ORDER BY ix.indisprimary DESC, pidx.indexname
    """, (schema, table))


def get_foreign_keys(conn, schema: str, table: str) -> list:
    """Return foreign key info for *schema*.*table*."""
    return exec_query(conn, """
        SELECT
            tc.constraint_name,
            STRING_AGG(kcu.column_name, ', '
                       ORDER BY kcu.ordinal_position) AS columns,
            ccu.table_schema || '.' || ccu.table_name AS ref_table,
            STRING_AGG(ccu.column_name, ', '
                       ORDER BY kcu.ordinal_position) AS ref_columns,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON  tc.constraint_name   = kcu.constraint_name
            AND tc.constraint_schema = kcu.constraint_schema
            AND tc.table_name        = kcu.table_name
        JOIN information_schema.referential_constraints rc
            ON  tc.constraint_name   = rc.constraint_name
            AND tc.constraint_schema = rc.constraint_schema
        JOIN information_schema.constraint_column_usage ccu
            ON  rc.unique_constraint_name   = ccu.constraint_name
            AND rc.unique_constraint_schema = ccu.constraint_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = %s
          AND tc.table_name   = %s
        GROUP BY tc.constraint_name, ccu.table_schema, ccu.table_name,
                 rc.update_rule, rc.delete_rule
        ORDER BY tc.constraint_name
    """, (schema, table))


def get_columns_for_export(conn, schema: str, table: str) -> list:
    """Extended column query used by the Data Dictionary exporter.

    Includes UDT name, raw precision/scale, and pg_description comments.
    """
    return exec_query(conn, """
        SELECT
            c.ordinal_position,
            c.column_name,
            c.data_type,
            c.udt_name,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            c.is_nullable,
            c.column_default,
            COALESCE(STRING_AGG(DISTINCT
                CASE tc.constraint_type
                    WHEN 'PRIMARY KEY' THEN 'PK'
                    WHEN 'FOREIGN KEY' THEN 'FK'
                    WHEN 'UNIQUE'      THEN 'UQ'
                    ELSE NULL
                END, ', '), '') AS constraints,
            d.description
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON  c.table_schema = kcu.table_schema
            AND c.table_name   = kcu.table_name
            AND c.column_name  = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON  kcu.constraint_name   = tc.constraint_name
            AND kcu.constraint_schema = tc.constraint_schema
            AND kcu.table_name        = tc.table_name
        LEFT JOIN pg_catalog.pg_description d
            ON  d.objoid = (
                    SELECT pg_class.oid FROM pg_class
                    JOIN   pg_namespace
                           ON pg_namespace.oid = pg_class.relnamespace
                    WHERE  pg_class.relname    = %s
                      AND  pg_namespace.nspname = %s
                )
            AND d.objsubid = c.ordinal_position
        WHERE c.table_schema = %s AND c.table_name = %s
        GROUP BY c.ordinal_position, c.column_name, c.data_type,
                 c.udt_name, c.character_maximum_length,
                 c.numeric_precision, c.numeric_scale,
                 c.is_nullable, c.column_default, d.description
        ORDER BY c.ordinal_position
    """, (table, schema, schema, table))
