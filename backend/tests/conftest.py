import os
os.environ['DATABASE_URL']='sqlite:///./test.db'; os.environ['LLM_PROVIDER']='mock'; os.environ['CAMPAIGN_PROVIDER']='mock'; os.environ['EMAIL_PROVIDER']='mock'
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine
from app.main import app
from app.auth import reset_rate_limit
@pytest.fixture(autouse=True)
def reset():
    reset_rate_limit()
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); yield
@pytest.fixture
def anon(): return TestClient(app)   # no session — for auth/negative tests
@pytest.fixture
def client():
    # Authenticated console client: logs in once and sends the bearer token on
    # every request (the full-gate default for the admin API).
    c=TestClient(app)
    tok=c.post('/api/v1/auth/login',json={'username':'root','password':'root'}).json()['access_token']
    c.headers.update({'Authorization':f'Bearer {tok}'})
    return c
