"""scenario quality-assessment fields"""
from alembic import op
import sqlalchemy as sa
revision="0003_scenario_quality"; down_revision="0002_hr_fields"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column('scenarios',sa.Column('quality_score',sa.Float(),nullable=True))
    op.add_column('scenarios',sa.Column('quality_notes',sa.JSON(),nullable=False,server_default='[]'))
def downgrade():
    op.drop_column('scenarios','quality_notes'); op.drop_column('scenarios','quality_score')
