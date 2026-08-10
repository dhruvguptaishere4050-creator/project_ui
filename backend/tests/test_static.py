from pathlib import Path

import pytest

from app.config import DEV_SECRET_KEY, Settings
from app.main import resolve_static_file


def test_static_paths_cannot_escape_the_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    (bundle / "assets").mkdir(parents=True)
    (bundle / "index.html").write_text("<html></html>")
    (bundle / "assets" / "app.js").write_text("console.log(1)")
    secret = tmp_path / "secret.env"
    secret.write_text("SECRET_KEY=leaked")

    index = bundle / "index.html"
    assert resolve_static_file(bundle, "assets/app.js") == bundle / "assets" / "app.js"
    assert resolve_static_file(bundle, "") == index
    assert resolve_static_file(bundle, "dashboard") == index
    assert resolve_static_file(bundle, "../secret.env") == index
    assert resolve_static_file(bundle, "../../etc/passwd") == index
    assert resolve_static_file(bundle, "/etc/passwd") == index


def test_production_requires_a_real_secret_key() -> None:
    dev = Settings(_env_file=None, secret_key=DEV_SECRET_KEY)
    dev.validate_for_runtime()

    production = Settings(_env_file=None, environment="production", secret_key=DEV_SECRET_KEY)
    with pytest.raises(RuntimeError):
        production.validate_for_runtime()

    Settings(
        _env_file=None, environment="production", secret_key="a-real-random-key"
    ).validate_for_runtime()
