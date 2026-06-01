# Installation Guide

## System Requirements

### Ubuntu 22.04+ (Clean Server)

```bash
# System packages
sudo apt-get update
sudo apt-get install -y \
  git \
  python3.12 \
  python3.12-venv \
  python3.12-dev \
  python3-pip \
  build-essential

# Optional: Redis server (required for production working memory)
sudo apt-get install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### macOS

```bash
# Using Homebrew
brew install python@3.12 redis

# Start Redis
brew services start redis
```

### Other Linux Distributions

Ensure these are installed:
- Python 3.12 or later
- python3-venv
- python3-dev
- git
- build-essential (or equivalent: gcc, make, etc.)
- Optional: Redis server for production working memory

## Python Virtual Environment Setup

Create and activate a Python virtual environment:

```bash
# Create venv
python3.12 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

## Install Dependencies

Install the package with development extras:

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev,memory]"

# Verify installation
python -m mas --version
```

### Dependency Groups

- **Base**: Core library dependencies (none currently beyond stdlib)
- **dev**: Testing and development (pytest>=8, pytest-cov)
- **memory** (optional): Redis working memory (redis>=5.0)

## Redis Configuration

For development/testing without Redis:

```python
# Working memory gracefully handles missing Redis
from mas.memory import RedisWorkingMemory

# If Redis is not available, operations are no-ops
memory = RedisWorkingMemory()  # redis_client=None defaults to no-op mode
```

For production, connect to Redis:

```python
import redis
from mas.memory import RedisWorkingMemory

redis_client = redis.asyncio.from_url("redis://localhost:6379")
memory = RedisWorkingMemory(redis_client=redis_client)
```

## Verify Installation

Run the test suite to confirm everything is working:

```bash
pytest -v
pytest --cov=src/mas tests/  # With coverage
```

## Troubleshooting

### Module not found errors

Ensure you've activated the virtual environment and installed with `-e`:

```bash
source venv/bin/activate
pip install -e ".[dev,memory]"
```

### Redis connection errors

If you see Redis errors and don't need working memory for your task:

```python
# Create episodic memory without Redis
from mas.memory import EpisodicMemoryStoreImpl
episodic = EpisodicMemoryStoreImpl()

# For working memory, omit Redis connection
from mas.memory import RedisWorkingMemory
working = RedisWorkingMemory()  # Operates in no-op mode
```

### Python version mismatch

Verify you're using Python 3.12+:

```bash
python --version
# Should output: Python 3.12.x or later
```

If not, ensure Python 3.12 is installed and use `python3.12` explicitly:

```bash
python3.12 -m venv venv
source venv/bin/activate
python --version
```

## Deactivate Virtual Environment

When done working:

```bash
deactivate
```
