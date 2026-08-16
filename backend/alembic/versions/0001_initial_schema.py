"""Initial schema: orgs, users, agents, conversations, messages, executions, memory.

The baseline migration. It reproduces exactly what `Base.metadata.create_all`
used to build at startup, which is why it is one revision rather than a
history: the project had no migrations before this, so there is nothing
earlier to migrate from. It was produced with `alembic revision --autogenerate`
against the models and is checked against them by tests/test_migrations.py.

Revision ID: 0001_initial_schema
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('orgs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('plan', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('orgs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orgs_slug'), ['slug'], unique=True)

    op.create_table('agents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('system_prompt', sa.Text(), nullable=False),
    sa.Column('enabled_tools', sa.Text(), nullable=False),
    sa.Column('teammate_ids', sa.Text(), nullable=False),
    sa.Column('requires_approval', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_agents_org_id'), ['org_id'], unique=False)

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('org_id', 'email', name='uq_user_org_email')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_org_id'), ['org_id'], unique=False)

    op.create_table('conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('agent_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_conversations_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversations_user_id'), ['user_id'], unique=False)

    op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notes_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notes_user_id'), ['user_id'], unique=False)

    op.create_table('user_facts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('fact', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_facts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_facts_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_facts_user_id'), ['user_id'], unique=False)

    op.create_table('executions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('agent_id', sa.Integer(), nullable=True),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('pending_action', sa.Text(), nullable=True),
    sa.Column('steps', sa.Text(), nullable=False),
    sa.Column('tokens_used', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_executions_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_executions_user_id'), ['user_id'], unique=False)

    op.create_table('memory_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=True),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('memory_documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_memory_documents_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_memory_documents_user_id'), ['user_id'], unique=False)

    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('tool_calls', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_messages_conversation_id'), ['conversation_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_conversation_id'))

    op.drop_table('messages')
    with op.batch_alter_table('memory_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_memory_documents_user_id'))
        batch_op.drop_index(batch_op.f('ix_memory_documents_org_id'))

    op.drop_table('memory_documents')
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_executions_user_id'))
        batch_op.drop_index(batch_op.f('ix_executions_org_id'))

    op.drop_table('executions')
    with op.batch_alter_table('user_facts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_facts_user_id'))
        batch_op.drop_index(batch_op.f('ix_user_facts_org_id'))

    op.drop_table('user_facts')
    with op.batch_alter_table('notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notes_user_id'))
        batch_op.drop_index(batch_op.f('ix_notes_org_id'))

    op.drop_table('notes')
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversations_user_id'))
        batch_op.drop_index(batch_op.f('ix_conversations_org_id'))

    op.drop_table('conversations')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_org_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_agents_org_id'))

    op.drop_table('agents')
    with op.batch_alter_table('orgs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orgs_slug'))

    op.drop_table('orgs')
