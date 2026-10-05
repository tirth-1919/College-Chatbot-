import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app.core.database import Base, get_db
from backend.app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.models.knowledge import KnowledgeGap
from backend.app.models.user import User
from backend.app.core.security import create_access_token

def _headers(user):
    token = create_access_token({'sub': user.id, 'role': user.role, 'is_admin': True})
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def gap_env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    admin = User(id=str(uuid.uuid4()), email='bulk-super@example.test', full_name='Bulk Super', role='SUPER_ADMIN', is_active=True)
    db.add(admin)
    db.add_all([
        KnowledgeGap(id=str(uuid.uuid4()), user_query='open', status='OPEN', resolved=False),
        KnowledgeGap(id=str(uuid.uuid4()), user_query='resolved', status='RESOLVED', resolved=True, resolved_at=datetime.now(timezone.utc), resolved_by='someone'),
    ])
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app, raise_server_exceptions=False), db, admin
    app.dependency_overrides.pop(get_db, None)
    db.close()


def test_resolve_all_only_open_gaps_and_is_idempotent(gap_env):
    client, db_session, admin = gap_env
    response = client.post('/api/v1/admin/knowledge-gaps/resolve-all', headers=_headers(admin))
    assert response.status_code == 200
    assert response.json()['resolved_count'] == 1
    assert db_session.query(KnowledgeGap).filter(KnowledgeGap.status == 'OPEN').count() == 0
    response = client.post('/api/v1/admin/knowledge-gaps/resolve-all', headers=_headers(admin))
    assert response.status_code == 200
    assert response.json()['resolved_count'] == 0
