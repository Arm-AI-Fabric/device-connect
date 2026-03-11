"""Root conftest for cross-repo integration tests.

Infrastructure:
    - Session-scoped Docker Compose (NATS + etcd + registry)
    - Dev mode: no TLS, no JWT (DEVICE_CONNECT_ALLOW_INSECURE=true)

Fixtures:
    - device_spawner: DeviceFactory using device_connect_sdk package
    - event_capture: EventCollector for NATS event capture
    - event_injector: EventInjector for simulating device events
    - mock_orchestrator: Rule-based orchestrator (no LLM)

"""

import logging
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure drivers/ and fixtures/ are importable
ITEST_ROOT = Path(__file__).parent
if str(ITEST_ROOT) not in sys.path:
    sys.path.insert(0, str(ITEST_ROOT))

from fixtures.infrastructure import (
    DockerComposeManager,
    clear_device_registry,
    wait_for_all_services,
)

logger = logging.getLogger(__name__)

DEFAULT_NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")


# ── Session-scoped infrastructure ──────────────────────────────────

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def infrastructure():
    """Start Docker Compose infrastructure for the test session."""
    manager = DockerComposeManager()
    try:
        await manager.start()
        await wait_for_all_services()
        logger.info("Infrastructure ready")
        yield manager
    finally:
        if manager._started_by_us:
            keep = os.getenv("ITEST_KEEP_INFRA", "").lower() in ("1", "true", "yes")
            if not keep:
                await manager.stop()
            else:
                logger.info("Keeping infrastructure running (ITEST_KEEP_INFRA=1)")


@pytest.fixture
def nats_url(infrastructure) -> str:
    return DEFAULT_NATS_URL


# ── Device spawner (uses device_connect_sdk) ────────────────────────────

@pytest.fixture
async def device_spawner(infrastructure, nats_url):
    """Factory for spawning simulated devices via device_connect_sdk."""
    from fixtures.devices import DeviceFactory

    factory = DeviceFactory(messaging_url=nats_url)
    try:
        yield factory
    finally:
        await factory.cleanup()


# ── Event capture ──────────────────────────────────────────────────

@pytest.fixture
async def event_capture(infrastructure, nats_url):
    """NATS event capture utility."""
    from fixtures.events import EventCollector

    collector = EventCollector(nats_url=nats_url)
    async with collector:
        yield collector


# ── Event injector ─────────────────────────────────────────────────

@pytest.fixture
async def event_injector(infrastructure, nats_url):
    """NATS event injection utility."""
    from fixtures.inject import EventInjector

    injector = EventInjector(nats_url=nats_url)
    async with injector:
        yield injector


# ── Mock orchestrator (no LLM) ────────────────────────────────────

@pytest.fixture
async def mock_orchestrator(infrastructure, nats_url):
    """Rule-based orchestrator for fast tests (no LLM)."""
    from fixtures.orchestrator import MockOrchestrator

    orchestrator = MockOrchestrator(nats_url=nats_url)
    async with orchestrator:
        yield orchestrator


# ── Registry cleanup ──────────────────────────────────────────────

@pytest.fixture
async def clear_registry(infrastructure):
    """Clear all devices from registry before test."""
    count = await clear_device_registry()
    logger.info(f"Registry cleared: {count} devices removed")
    yield count


# ── Pytest hooks ──────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires Docker infrastructure")
    config.addinivalue_line("markers", "llm: requires real LLM API key")
    config.addinivalue_line("markers", "slow: takes > 30 seconds")
    config.addinivalue_line("markers", "conformance: messaging backend conformance test")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
