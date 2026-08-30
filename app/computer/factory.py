"""Select ComputerDriver: Windows real driver on Windows, Mock elsewhere."""

from __future__ import annotations

import os
import sys

from app.computer.base import ComputerDriver
from app.computer.controller import ComputerController
from app.computer.mock_driver import MockComputerDriver
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_driver(*, force_mock: bool | None = None) -> ComputerDriver:
    if force_mock is None:
        force_mock = os.environ.get("COMPUTER_USE_MOCK", "").lower() in ("1", "true", "yes")
    if force_mock or not sys.platform.startswith("win"):
        logger.info("computer_driver_selected", driver="mock")
        return MockComputerDriver()
    try:
        from app.computer.windows_driver import WindowsComputerDriver

        driver = WindowsComputerDriver()
        logger.info("computer_driver_selected", driver="windows")
        return driver
    except Exception as exc:
        logger.warning("windows_driver_unavailable", error=str(exc))
        return MockComputerDriver()


def create_controller(*, force_mock: bool | None = None) -> ComputerController:
    return ComputerController(driver=create_driver(force_mock=force_mock))
