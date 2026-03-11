"""Integration tests for D2D (Device-to-Device) direct RPC invocation.

Tests that one device can call another device's RPC directly via NATS,
without an orchestrator in the loop.
"""

import asyncio
import json
import pytest

import nats as nats_client


SETTLE_TIME = 0.2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_d2d_direct_rpc_sensor_reading(device_spawner):
    """Device A (robot) calls Device B (sensor) get_reading directly via NATS."""
    sensor, sensor_driver = await device_spawner.spawn_sensor(
        "itest-d2d-sensor", initial_temp=25.0, initial_humidity=55.0,
    )
    robot, robot_driver = await device_spawner.spawn_robot("itest-d2d-robot-caller")
    await asyncio.sleep(SETTLE_TIME)

    # Robot calls sensor's get_reading RPC directly via NATS
    nc = await nats_client.connect("nats://localhost:4222")
    try:
        request = {
            "jsonrpc": "2.0",
            "id": "d2d-rpc-1",
            "method": "get_reading",
            "params": {"unit": "celsius"},
        }
        response = await nc.request(
            "device-connect.default.itest-d2d-sensor.cmd",
            json.dumps(request).encode(),
            timeout=5.0,
        )
        data = json.loads(response.data)
        assert "result" in data, f"RPC failed: {data}"
        assert data["result"]["temperature"] == 25.0
        assert data["result"]["humidity"] == 55.0
    finally:
        await nc.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_d2d_direct_rpc_robot_status(device_spawner):
    """Direct RPC to get robot status without orchestrator."""
    robot, robot_driver = await device_spawner.spawn_robot("itest-d2d-status-robot")
    await asyncio.sleep(SETTLE_TIME)

    nc = await nats_client.connect("nats://localhost:4222")
    try:
        request = {
            "jsonrpc": "2.0",
            "id": "d2d-rpc-2",
            "method": "get_status",
            "params": {},
        }
        response = await nc.request(
            "device-connect.default.itest-d2d-status-robot.cmd",
            json.dumps(request).encode(),
            timeout=5.0,
        )
        data = json.loads(response.data)
        assert "result" in data
        assert data["result"]["busy"] is False
    finally:
        await nc.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_d2d_rpc_to_unknown_device(device_spawner):
    """RPC to a non-existent device should timeout."""
    nc = await nats_client.connect("nats://localhost:4222")
    try:
        request = {
            "jsonrpc": "2.0",
            "id": "d2d-rpc-missing",
            "method": "get_reading",
            "params": {},
        }
        with pytest.raises(Exception):  # nats.errors.TimeoutError
            await nc.request(
                "device-connect.default.nonexistent-device.cmd",
                json.dumps(request).encode(),
                timeout=2.0,
            )
    finally:
        await nc.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_d2d_rpc_chain(device_spawner, event_capture):
    """Chain: dispatch robot → robot cleans → emits cleaning_finished."""
    robot, robot_driver = await device_spawner.spawn_robot(
        "itest-d2d-chain-robot", clean_duration=0.3,
    )
    await asyncio.sleep(SETTLE_TIME)

    async with event_capture.subscribe("device-connect.*.itest-d2d-chain-robot.event.*") as events:
        nc = await nats_client.connect("nats://localhost:4222")
        try:
            request = {
                "jsonrpc": "2.0",
                "id": "d2d-chain-1",
                "method": "dispatch_robot",
                "params": {"zone_id": "zone-chain"},
            }
            response = await nc.request(
                "device-connect.default.itest-d2d-chain-robot.cmd",
                json.dumps(request).encode(),
                timeout=5.0,
            )
            data = json.loads(response.data)
            assert data["result"]["status"] == "accepted"
        finally:
            await nc.close()

        event = await events.wait_for("cleaning_finished", timeout=10)
        assert event.data["zone_id"] == "zone-chain"
