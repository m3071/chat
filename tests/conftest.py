import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

TEST_ROOT = Path(__file__).resolve().parents[1]
os.environ["RUNTIME_CONFIG_PATH"] = str(TEST_ROOT / "tests-runtime-config.json")
os.environ["INTERNAL_API_KEY"] = ""
os.environ["WAZUH_SHARED_SECRET"] = ""

sys.path.append(str(TEST_ROOT / "apps" / "api"))

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
      db = TestingSessionLocal()
      try:
          yield db
      finally:
          db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    runtime_config_path = Path(os.environ["RUNTIME_CONFIG_PATH"])
    if runtime_config_path.exists():
        runtime_config_path.unlink()
