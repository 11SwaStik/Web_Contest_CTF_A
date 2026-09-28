import os
import tempfile

import pytest


@pytest.fixture()
def client():
    # Use a throwaway SQLite file so tests never touch a real DB.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    os.environ["DB_PATH"] = path

    # Import after DB_PATH is set (Config reads it at import time).
    import importlib
    import app as app_pkg
    import app.config as config_mod
    import app.db as db_mod
    importlib.reload(config_mod)
    importlib.reload(db_mod)
    importlib.reload(app_pkg)

    application = app_pkg.create_app()
    application.config.update(TESTING=True)
    with application.test_client() as c:
        yield c

    if os.path.exists(path):
        os.remove(path)
