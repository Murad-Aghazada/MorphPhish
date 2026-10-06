"""training assignments (assign/track corrective training)"""
from alembic import op
import sqlalchemy as sa
revision="0004_training_assignments"; down_revision="0003_scenario_quality"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table('training_assignments',
        sa.Column('id',sa.String(),primary_key=True),
        sa.Column('employee_id',sa.String(),sa.ForeignKey('employees.id',ondelete='CASCADE'),nullable=False),
        sa.Column('topic',sa.String(80),nullable=False),
        sa.Column('priority',sa.String(20),nullable=False),
        sa.Column('recommendation',sa.Text(),nullable=False),
        sa.Column('status',sa.String(20),nullable=False,server_default='assigned'),
        sa.Column('assigned_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('completed_at',sa.DateTime(timezone=True),nullable=True),
        sa.UniqueConstraint('employee_id','topic',name='uq_training_assignment'))
    op.create_index('ix_training_assignments_employee_id','training_assignments',['employee_id'])
    op.create_index('ix_training_assignments_status','training_assignments',['status'])
def downgrade():
    op.drop_table('training_assignments')
