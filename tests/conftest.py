import importlib
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

for service_dir in [
    ROOT / "apps" / "notification-service",
    ROOT / "apps" / "api-gateway",
    ROOT / "apps" / "user-service",
]:
    if str(service_dir) in sys.path:
        sys.path.remove(str(service_dir))

sys.path.insert(0, str(ROOT / "apps" / "user-service"))
# Keep the gateway app isolated from the user-service package so tests do not import the wrong app module.
sys.path.insert(1, str(ROOT / "apps" / "notification-service"))

unique_db_name = f"test_user_service_{uuid.uuid4().hex}.db"
unique_db_path = ROOT / unique_db_name
if unique_db_path.exists():
    unique_db_path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{unique_db_path}"
os.environ["USER_SERVICE_URL"] = "http://user-service:8001"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://notification-service:8002"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

# Ensure the app modules are initialized against the fresh test database, not an older SQLite file.
import app.core.config as config_module
import app.db.session as session_module
import app.models.user as user_model_module

importlib.reload(config_module)
importlib.reload(session_module)
importlib.reload(user_model_module)

session_module.Base.metadata.create_all(bind=session_module.engine)
