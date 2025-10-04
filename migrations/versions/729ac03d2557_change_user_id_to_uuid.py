"""Change user id to UUID safely

Revision ID: 729ac03d2557
Revises: f9b8d5f71a00
Create Date: 2025-10-04

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '729ac03d2557'
down_revision = 'f9b8d5f71a00'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """检查列是否存在"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table
          AND COLUMN_NAME = :column
        """),
        {"table": table_name, "column": column_name}
    ).fetchone()
    return bool(result)


def drop_fk_if_exists(table_name, fk_name):
    """安全删除外键，如果不存在则跳过"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
        SELECT CONSTRAINT_NAME 
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() 
          AND TABLE_NAME = :table 
          AND CONSTRAINT_NAME = :fk
        """),
        {"table": table_name, "fk": fk_name}
    ).fetchone()
    if result:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")


def upgrade():
    connection = op.get_bind()

    # --- 1. users 表新增临时列 uuid ---
    if not column_exists("users", "id_uuid"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("id_uuid", sa.String(36), nullable=True))

    # --- 2. 填充 id_uuid 数据 ---
    users = connection.execute(sa.text("SELECT id, id_uuid FROM users")).fetchall()
    for row in users:
        old_id, existing_uuid = row
        if not existing_uuid:
            new_id = str(uuid.uuid4())
            connection.execute(sa.text(
                "UPDATE users SET id_uuid = :new_id WHERE id = :old_id"
            ), {"new_id": new_id, "old_id": old_id})

    # --- 3. wallet_users 表新增临时列 uuid ---
    if not column_exists("wallet_users", "user_id_uuid"):
        with op.batch_alter_table("wallet_users") as batch_op:
            batch_op.add_column(sa.Column("user_id_uuid", sa.String(36), nullable=True))

    # --- 4. 填充 wallet_users.user_id_uuid 数据 ---
    connection.execute(sa.text("""
        UPDATE wallet_users wu
        JOIN users u ON wu.user_id = u.id
        SET wu.user_id_uuid = u.id_uuid
        WHERE wu.user_id_uuid IS NULL
    """))

    # --- 5. user_accounts 表新增临时列 uuid ---
    if not column_exists("user_accounts", "user_id_uuid"):
        with op.batch_alter_table("user_accounts") as batch_op:
            batch_op.add_column(sa.Column("user_id_uuid", sa.String(36), nullable=True))

    # --- 6. 填充 user_accounts.user_id_uuid 数据 ---
    connection.execute(sa.text("""
        UPDATE user_accounts ua
        JOIN users u ON ua.user_id = u.id
        SET ua.user_id_uuid = u.id_uuid
        WHERE ua.user_id_uuid IS NULL
    """))

    # --- 7. 删除旧外键，如果存在 ---
    drop_fk_if_exists("wallet_users", "wallet_users_ibfk_1")
    drop_fk_if_exists("user_accounts", "user_accounts_ibfk_1")

    # --- 8. 删除旧列，改名新列 ---
    with op.batch_alter_table("users") as batch_op:
        if column_exists("users", "id"):
            batch_op.drop_column("id")
        batch_op.alter_column("id_uuid", new_column_name="id", nullable=False)

    with op.batch_alter_table("wallet_users") as batch_op:
        if column_exists("wallet_users", "user_id"):
            batch_op.drop_column("user_id")
        batch_op.alter_column("user_id_uuid", new_column_name="user_id", nullable=False)
        batch_op.create_foreign_key(
            "wallet_users_ibfk_1",
            "users",
            ["user_id"],
            ["id"]
        )

    with op.batch_alter_table("user_accounts") as batch_op:
        if column_exists("user_accounts", "user_id"):
            batch_op.drop_column("user_id")
        batch_op.alter_column("user_id_uuid", new_column_name="user_id", nullable=False)
        batch_op.create_foreign_key(
            "user_accounts_ibfk_1",
            "users",
            ["user_id"],
            ["id"]
        )


def downgrade():
    raise NotImplementedError("Downgrade is not supported for UUID migration.")
