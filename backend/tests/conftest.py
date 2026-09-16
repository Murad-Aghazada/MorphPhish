import os
os.environ['DATABASE_URL']='sqlite:///./test.db'; os.environ['LLM_PROVIDER']='mock'; os.environ['CAMPAIGN_PROVIDER']='mock'; os.environ['EMAIL_PROVIDER']='mock'
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine
from app.main import app
@pytest.fixture(autouse=True)
def reset():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); yield
@pytest.fixture
def client(): return TestClient(app)
