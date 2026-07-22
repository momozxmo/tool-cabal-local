"""Create authentication, session, workspace, and job tables.

Revision ID: 20260722_auth_sessions
Revises:
Create Date: 2026-07-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260722_auth_sessions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role in ('admin', 'member')", name='ck_users_role'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table(
        'web_sessions',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_web_sessions_user_id', 'web_sessions', ['user_id'])
    op.create_index('ix_web_sessions_token_hash', 'web_sessions', ['token_hash'], unique=True)

    op.create_table(
        'pairing_tokens',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pairing_tokens_user_id', 'pairing_tokens', ['user_id'])
    op.create_index('ix_pairing_tokens_token_hash', 'pairing_tokens', ['token_hash'], unique=True)

    op.create_table(
        'aztek_sessions',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('encrypted_state', sa.Text(), nullable=False),
        sa.Column('account_label', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('expires_hint_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_aztek_sessions_user_id', 'aztek_sessions', ['user_id'], unique=True)

    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('owner_user_id', sa.String(length=32), nullable=False),
        sa.Column('mode', sa.String(length=32), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=False),
        sa.Column('game', sa.String(length=255), nullable=True),
        sa.Column('criteria', sa.JSON(), nullable=False),
        sa.Column('occurrences', sa.JSON(), nullable=False),
        sa.Column('group_meta', sa.JSON(), nullable=False),
        sa.Column('skipped', sa.JSON(), nullable=False),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('not_found', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workspaces_owner_user_id', 'workspaces', ['owner_user_id'])

    op.create_table(
        'pending_imports',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('owner_user_id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.String(length=32), nullable=False),
        sa.Column('sheets', sa.JSON(), nullable=False),
        sa.Column('skipped', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pending_imports_owner_user_id', 'pending_imports', ['owner_user_id'])
    op.create_index('ix_pending_imports_workspace_id', 'pending_imports', ['workspace_id'])

    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('owner_user_id', sa.String(length=32), nullable=False),
        sa.Column('workspace_id', sa.String(length=32), nullable=True),
        sa.Column('tool', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('log', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_jobs_owner_user_id', 'jobs', ['owner_user_id'])
    op.create_index('ix_jobs_workspace_id', 'jobs', ['workspace_id'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('tool', sa.String(length=64), nullable=True),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('account_label', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('ix_jobs_workspace_id', table_name='jobs')
    op.drop_index('ix_jobs_owner_user_id', table_name='jobs')
    op.drop_table('jobs')

    op.drop_index('ix_pending_imports_workspace_id', table_name='pending_imports')
    op.drop_index('ix_pending_imports_owner_user_id', table_name='pending_imports')
    op.drop_table('pending_imports')

    op.drop_index('ix_workspaces_owner_user_id', table_name='workspaces')
    op.drop_table('workspaces')

    op.drop_index('ix_aztek_sessions_user_id', table_name='aztek_sessions')
    op.drop_table('aztek_sessions')

    op.drop_index('ix_pairing_tokens_token_hash', table_name='pairing_tokens')
    op.drop_index('ix_pairing_tokens_user_id', table_name='pairing_tokens')
    op.drop_table('pairing_tokens')

    op.drop_index('ix_web_sessions_token_hash', table_name='web_sessions')
    op.drop_index('ix_web_sessions_user_id', table_name='web_sessions')
    op.drop_table('web_sessions')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
