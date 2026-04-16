# Alembic Notes

## Enum migrations in PostgreSQL

Rule: any `ALTER TYPE ... ADD VALUE` must be wrapped in `with op.get_context().autocommit_block():`.

Why:
- PostgreSQL commits a new enum value only after the DDL transaction is finished.
- Alembic normally runs the whole migration inside one transaction.
- If you add a new enum value and then use it in `UPDATE`/`INSERT` in the same transaction, PostgreSQL raises `UnsafeNewEnumValueUsageError`.

Correct pattern:

```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                text("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'NEW_VALUE'")
            )

        op.execute(
            text("UPDATE orders SET status = 'NEW_VALUE' WHERE ...")
        )
```

Do not:
- put `ALTER TYPE ... ADD VALUE` and DML that uses the new value in one `op.execute()`;
- put both steps in the same Alembic transaction block;
- use `DO $$ ... $$` here when a simple `ADD VALUE IF NOT EXISTS` is enough.
