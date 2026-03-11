# Device Connect Integration Tests

Cross-repo integration tests for the Device Connect platform. Validates that
[device-connect-sdk](https://github.com/arm/device-connect-sdk),
[device-connect-server](https://github.com/arm/device-connect-server), and
[device-connect-agent-tools](https://github.com/arm/device-connect-agent-tools)
work together end-to-end.

## Architecture

```
device-connect-tests/
├── tests/                  # Test modules
│   ├── test_device_lifecycle.py       # Device connect/disconnect/heartbeat
│   ├── test_d2d_events.py             # Device-to-device events
│   ├── test_d2d_rpc.py                # Device-to-device RPC
│   ├── test_d2o_events.py             # Device-to-orchestrator events
│   ├── test_d2o_rpc.py                # Device-to-orchestrator RPC
│   ├── test_sensor_device.py          # Sensor device patterns
│   ├── test_multi_device_scenario.py  # Multi-device scenarios
│   ├── test_tools_discover.py         # Agent tools: device discovery
│   ├── test_tools_invoke.py           # Agent tools: function invocation
│   ├── test_strands_agent.py          # Strands agent integration
│   ├── test_llm_orchestrator.py       # LLM orchestrator (requires API key)
│   └── test_messaging_conformance.py  # Messaging backend conformance
├── fixtures/               # Shared pytest fixtures
│   ├── infrastructure.py   # Docker Compose lifecycle management
│   ├── devices.py          # Device factory for spawning test devices
│   ├── events.py           # NATS event capture utilities
│   ├── inject.py           # Event injection utilities
│   └── orchestrator.py     # Orchestrator fixtures (mock + real LLM)
├── conftest.py             # Root conftest with session-scoped fixtures
├── docker-compose-itest.yml # NATS + etcd + registry services
├── requirements.txt        # Test dependencies
└── pytest.ini              # Pytest configuration
```

## Infrastructure

Tests run against Docker Compose services in **dev mode** (no TLS, no JWT):

| Service           | Image                        | Port  |
|-------------------|------------------------------|-------|
| NATS + JetStream  | `nats:2.10-alpine`           | 4222  |
| etcd              | `quay.io/coreos/etcd:v3.5.9` | 2379  |
| Device Registry   | Built from device-connect-server | 8000  |

The `infrastructure` session-scoped fixture manages the lifecycle automatically.

## Prerequisites

Clone all repos as siblings:

```
mkdir device-connect && cd device-connect
git clone https://github.com/arm/device-connect-sdk.git
git clone https://github.com/arm/device-connect-server.git
git clone https://github.com/arm/device-connect-agent-tools.git
git clone https://github.com/arm/device-connect-tests.git
```

## Setup

```bash
cd device-connect-tests
python -m venv .venv && source .venv/bin/activate

# Install all packages in editable mode
pip install -e ../device-connect-sdk
pip install -e "../device-connect-server[all]"
pip install -e "../device-connect-agent-tools[strands]"
pip install -r requirements.txt
```

## Running Tests

### Start infrastructure

```bash
docker compose -f docker-compose-itest.yml up -d
```

### Tier 1: Core integration tests (no LLM)

```bash
pytest tests/ -v -m "not llm" --timeout=120
```

### Tier 2: LLM tests (requires API key)

```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."

pytest tests/ -v -m "llm" --timeout=120
```

### Messaging conformance tests

```bash
pytest tests/test_messaging_conformance.py -v -m conformance --timeout=60
```

### Run everything

```bash
pytest tests/ -v --timeout=120
```

### Tear down

```bash
docker compose -f docker-compose-itest.yml down -v --remove-orphans
```

## Test Markers

| Marker        | Description                                          |
|---------------|------------------------------------------------------|
| `integration` | Requires Docker infrastructure (auto-added)          |
| `llm`         | Requires a real LLM API key                          |
| `slow`        | Takes > 30 seconds                                   |
| `conformance` | Messaging backend conformance tests                  |

## CI/CD

Tests run automatically via GitHub Actions (`.github/workflows/integration-tests.yml`):

- **On push** to `main`
- **On repository_dispatch** — triggered by pushes to `device-connect-sdk`, `device-connect-server`, or `device-connect-agent-tools`
- **On schedule** — weekdays at 6 AM UTC
- **Manual** — via `workflow_dispatch`

### CI Jobs

1. **integration-tests** — Tier 1 (no LLM), runs first
2. **llm-tests** — Tier 2 (requires `OPENAI_API_KEY` secret), runs after Tier 1
3. **conformance-tests** — Messaging backend conformance, runs after Tier 1

## Environment Variables

| Variable                      | Default                  | Description                        |
|-------------------------------|--------------------------|------------------------------------|
| `NATS_URL`                    | `nats://localhost:4222`  | NATS server URL                    |
| `ETCD_URL`                    | `http://localhost:2379`  | etcd server URL                    |
| `DEVICE_CONNECT_ALLOW_INSECURE` | _(unset)_             | Set to `true` for dev mode         |
| `ITEST_KEEP_INFRA`           | _(unset)_                | Set to `1` to keep infra after run |
| `OPENAI_API_KEY`             | _(unset)_                | OpenAI API key for LLM tests       |
| `ANTHROPIC_API_KEY`          | _(unset)_                | Anthropic API key for LLM tests    |
