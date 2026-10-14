import os

env = os.getenv("DJANGO_ENV", "").lower()
debug = os.getenv("DEBUG", "False").lower() == "true"

if env in ["development", "dev", "local"] or (not env and debug):
    from .development import *  # noqa: F401, F403
else:
    from .production import *   # noqa: F401, F403
