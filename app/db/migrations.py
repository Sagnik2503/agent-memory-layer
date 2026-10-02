from sqlalchemy import text

_TABLES = ["expenses", "subscriptions", "budgets", "pending_alerts"]


def migrate_add_user_id(engine, default_user: str) -> None:
    """Add user_id to tables created before the multi-user schema.

    Safe to run repeatedly: checks column existence first. Fresh tables created
    by create_all already have user_id and are left alone.
    """
    with engine.begin() as conn:
        for table in _TABLES:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            if not rows:
                continue
            columns = [row[1] for row in rows]
            if "user_id" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN user_id VARCHAR(100) NOT NULL DEFAULT '{default_user}'"
                    )
                )
                print(f"[migrate] added user_id to {table}")
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id "
                    f"ON {table}(user_id)"
                )
            )


CANONICAL_CATEGORIES = (
    "food",
    "transport",
    "shopping",
    "bills",
    "entertainment",
    "health",
    "personal_care",
    "other",
)

# Legacy free-form values folded into the canonical vocabulary (GLOSSARY.md).
_CATEGORY_ALIASES = {"subscriptions": "bills"}


def migrate_normalize_categories(engine) -> None:
    """Rewrite non-canonical category values to the canonical vocabulary.

    Rows written before the enum existed (e.g. the stray "Subscriptions"
    value) fail ExpenseCategory validation in the repository, which takes down
    every endpoint that reads them. Safe to run repeatedly: canonical values
    and NULL (the overall Budget's marker) are left alone.
    """
    with engine.begin() as conn:
        for table in _TABLES:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            if not rows or "category" not in [row[1] for row in rows]:
                continue
            values = conn.execute(
                text(
                    f"SELECT DISTINCT category FROM {table} WHERE category IS NOT NULL"
                )
            ).fetchall()
            for (value,) in values:
                if value in CANONICAL_CATEGORIES:
                    continue
                normalized = _CATEGORY_ALIASES.get(value.lower(), "other")
                conn.execute(
                    text(
                        f"UPDATE {table} SET category = :normalized "
                        f"WHERE category = :value"
                    ),
                    {"normalized": normalized, "value": value},
                )
                print(
                    f"[migrate] normalized {table}.category "
                    f"{value!r} -> {normalized!r}"
                )
