"""employee HR provenance fields"""
from alembic import op
import sqlalchemy as sa
revision="0002_hr_fields"; down_revision="0001_initial"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column('employees',sa.Column('source',sa.String(40),nullable=False,server_default='manual'))
    op.add_column('employees',sa.Column('external_id',sa.String(64),nullable=True))
    op.create_index('ix_employees_source','employees',['source'])
    op.create_index('ix_employees_external_id','employees',['external_id'])
def downgrade():
    op.drop_index('ix_employees_external_id','employees'); op.drop_index('ix_employees_source','employees')
    op.drop_column('employees','external_id'); op.drop_column('employees','source')
