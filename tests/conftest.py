import os
import sys
import types
import base64
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("SEED_DEFAULT_USERS", "false")


try:
    import jose  # noqa: F401
except Exception:
    class JWTError(Exception):
        pass

    def _json_default(value):
        if hasattr(value, "timestamp"):
            return int(value.timestamp())
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def _encode(payload, key, algorithm="HS256"):
        del key, algorithm
        raw_payload = json.dumps(payload, default=_json_default).encode("utf-8")
        return base64.urlsafe_b64encode(raw_payload).decode("ascii")

    def _decode(token, key, algorithms=None):
        del key, algorithms
        try:
            padded_token = token + "=" * (-len(token) % 4)
            raw_payload = base64.urlsafe_b64decode(padded_token.encode("ascii"))
            return json.loads(raw_payload.decode("utf-8"))
        except Exception as exc:
            raise JWTError("Invalid token") from exc

    jose_stub = types.ModuleType("jose")
    jwt_stub = types.ModuleType("jose.jwt")
    jwt_stub.encode = _encode
    jwt_stub.decode = _decode
    jose_stub.JWTError = JWTError
    jose_stub.jwt = jwt_stub

    sys.modules["jose"] = jose_stub
    sys.modules["jose.jwt"] = jwt_stub


try:
    import mlflow.sklearn  # noqa: F401
except Exception:
    mlflow_stub = sys.modules.get("mlflow") or types.ModuleType("mlflow")
    mlflow_sklearn_stub = types.ModuleType("mlflow.sklearn")
    mlflow_sklearn_stub.load_model = lambda *args, **kwargs: None
    mlflow_sklearn_stub.log_model = lambda *args, **kwargs: None

    mlflow_stub.sklearn = mlflow_sklearn_stub
    mlflow_stub.set_tracking_uri = lambda *args, **kwargs: None
    mlflow_stub.set_experiment = lambda *args, **kwargs: None
    mlflow_stub.log_params = lambda *args, **kwargs: None
    mlflow_stub.log_metric = lambda *args, **kwargs: None
    mlflow_stub.set_tags = lambda *args, **kwargs: None

    sys.modules["mlflow"] = mlflow_stub
    sys.modules["mlflow.sklearn"] = mlflow_sklearn_stub
