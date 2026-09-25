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
