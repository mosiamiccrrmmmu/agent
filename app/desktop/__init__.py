"""Desktop application support — paths, lifecycle, secure secrets, local auth."""

from app.desktop.auth import LocalAuth
from app.desktop.lifecycle import BackendLifecycle
from app.desktop.paths import AppPaths, get_app_paths
from app.desktop.secrets import SecureSecretStore

__all__ = [
    "AppPaths",
    "get_app_paths",
    "BackendLifecycle",
    "SecureSecretStore",
    "LocalAuth",
]
