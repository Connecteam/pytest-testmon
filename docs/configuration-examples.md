# Configuration Examples

This document provides configuration examples for various scenarios using the xdist coordination feature.

## Basic Configurations

### Development Environment

```bash
# ~/.bashrc or ~/.zshrc
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
alias test="pytest --testmon -n auto"
alias test-debug="TESTMON_XDIST_DEBUG=true pytest --testmon -n auto -v"
```

### Project-Specific Configuration

Create `.env` file in project root:
```bash
# .env
TESTMON_XDIST_CONTROLLER_PRECREATION=true
TESTMON_XDIST_WORKER_TIMEOUT=30
```

Load in your test script:
```bash
#!/bin/bash
# scripts/test.sh
set -a
source .env
set +a

pytest --testmon -n auto "$@"
```

## CI/CD Configurations

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .[test]
        pip install pytest-testmon pytest-xdist
    
    - name: Run tests
      env:
        TESTMON_XDIST_CONTROLLER_PRECREATION: true
        TESTMON_XDIST_WORKER_TIMEOUT: 60  # Higher for CI
      run: |
        pytest --testmon -n auto --cov=myproject
    
    - name: Run tests with debug (on failure)
      if: failure()
      env:
        TESTMON_XDIST_CONTROLLER_PRECREATION: true
        TESTMON_XDIST_DEBUG: true
      run: |
        pytest --testmon -n 2 -v --tb=short
```

### GitLab CI

```yaml
# .gitlab-ci.yml
variables:
  TESTMON_XDIST_CONTROLLER_PRECREATION: "true"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - .testmondata

stages:
  - test

test:unit:
  stage: test
  image: python:3.9
  before_script:
    - pip install -e .[test]
  script:
    - pytest --testmon -n auto tests/unit/
  
test:integration:
  stage: test
  image: python:3.9
  variables:
    TESTMON_XDIST_WORKER_TIMEOUT: "120"  # Longer timeout for integration tests
  before_script:
    - pip install -e .[test]
  script:
    - pytest --testmon -n 4 tests/integration/
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    options {
        timeout(time: 1, unit: 'HOURS')
    }
    
    environment {
        TESTMON_XDIST_CONTROLLER_PRECREATION = 'true'
        TESTMON_XDIST_WORKER_TIMEOUT = '45'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install -e .[test]
                '''
            }
        }
        
        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh '''
                            . venv/bin/activate
                            pytest --testmon -n auto tests/unit/ --junit-xml=unit-results.xml
                        '''
                    }
                }
                
                stage('Integration Tests') {
                    environment {
                        TESTMON_XDIST_WORKER_TIMEOUT = '120'
                    }
                    steps {
                        sh '''
                            . venv/bin/activate
                            pytest --testmon -n 4 tests/integration/ --junit-xml=integration-results.xml
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            junit '*-results.xml'
        }
        failure {
            sh '''
                . venv/bin/activate
                TESTMON_XDIST_DEBUG=true pytest --testmon -n 2 -v --tb=short || true
            '''
        }
    }
}
```

### CircleCI

```yaml
# .circleci/config.yml
version: 2.1

executors:
  python-executor:
    docker:
      - image: cimg/python:3.9
    environment:
      TESTMON_XDIST_CONTROLLER_PRECREATION: true

jobs:
  test:
    executor: python-executor
    parallelism: 4  # CircleCI's parallelism
    steps:
      - checkout
      
      - restore_cache:
          keys:
            - v1-deps-{{ checksum "requirements.txt" }}
            - v1-deps-
      
      - run:
          name: Install dependencies
          command: |
            pip install -e .[test]
      
      - save_cache:
          key: v1-deps-{{ checksum "requirements.txt" }}
          paths:
            - ~/.cache/pip
      
      - run:
          name: Run tests
          command: |
            # Use CircleCI's test splitting
            TESTFILES=$(circleci tests glob "tests/**/test_*.py" | circleci tests split)
            pytest --testmon -n auto $TESTFILES
      
      - store_test_results:
          path: test-results

workflows:
  test-workflow:
    jobs:
      - test
```

## Docker Configurations

### Dockerfile for Testing

```dockerfile
# Dockerfile.test
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install pytest-testmon pytest-xdist

# Copy source code
COPY . .

# Set coordination environment
ENV TESTMON_XDIST_CONTROLLER_PRECREATION=true
ENV TESTMON_XDIST_WORKER_TIMEOUT=60

# Run tests
CMD ["pytest", "--testmon", "-n", "auto"]
```

### Docker Compose

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - TESTMON_XDIST_CONTROLLER_PRECREATION=true
      - TESTMON_XDIST_WORKER_TIMEOUT=60
      - TESTMON_XDIST_DEBUG=${DEBUG:-false}
    volumes:
      - .:/app
      - testmon-data:/app/.testmondata
    command: pytest --testmon -n auto

  test-watch:
    extends: test
    command: pytest-watch -- --testmon -n auto
    environment:
      - TESTMON_XDIST_CONTROLLER_PRECREATION=true
      - TESTMON_XDIST_CHECK_INTERVAL=0.05  # Faster for watch mode

volumes:
  testmon-data:
```

## Advanced Configurations

### Dynamic Worker Count

```python
# conftest.py
import os
import multiprocessing

def pytest_configure(config):
    """Dynamically set worker count based on system resources."""
    if hasattr(config.option, 'numprocesses'):
        if config.option.numprocesses == 'auto':
            # Use half of available CPUs for tests
            num_cpus = multiprocessing.cpu_count()
            config.option.numprocesses = max(1, num_cpus // 2)
```

### Environment-Specific Settings

```bash
#!/bin/bash
# scripts/test-env.sh

# Detect environment and set appropriate config
if [ -n "$CI" ]; then
    # CI environment
    export TESTMON_XDIST_CONTROLLER_PRECREATION=true
    export TESTMON_XDIST_WORKER_TIMEOUT=120
    export TESTMON_XDIST_DEBUG=false
    WORKERS="-n auto"
elif [ -n "$DOCKER_CONTAINER" ]; then
    # Docker environment
    export TESTMON_XDIST_CONTROLLER_PRECREATION=true
    export TESTMON_XDIST_WORKER_TIMEOUT=60
    WORKERS="-n 4"
else
    # Local development
    export TESTMON_XDIST_CONTROLLER_PRECREATION=true
    export TESTMON_XDIST_WORKER_TIMEOUT=30
    export TESTMON_XDIST_DEBUG=true
    WORKERS="-n auto"
fi

pytest --testmon $WORKERS "$@"
```

### Performance Tuning

```bash
# Fast configuration for small test suites
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_CHECK_INTERVAL=0.05    # 50ms
export TESTMON_XDIST_BACKOFF_FACTOR=1.2     # Gentle backoff
export TESTMON_XDIST_MAX_INTERVAL=0.5       # 500ms max

# Robust configuration for large test suites
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_CHECK_INTERVAL=0.2     # 200ms
export TESTMON_XDIST_BACKOFF_FACTOR=2.0     # Aggressive backoff
export TESTMON_XDIST_MAX_INTERVAL=5.0       # 5s max
export TESTMON_XDIST_WORKER_TIMEOUT=300     # 5 minutes
```

### Debugging Configuration

```bash
# scripts/test-debug.sh
#!/bin/bash

# Maximum debugging
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_DEBUG=true
export PYTEST_VERBOSE="-vv"
export PYTEST_CAPTURE="--capture=no"
export PYTEST_TB="--tb=long"

# Run specific test with full debugging
pytest --testmon -n 2 \
    $PYTEST_VERBOSE \
    $PYTEST_CAPTURE \
    $PYTEST_TB \
    --log-cli-level=DEBUG \
    "$@"
```

## Platform-Specific Configurations

### macOS

```bash
# ~/.zshrc
export TESTMON_XDIST_CONTROLLER_PRECREATION=true

# Handle macOS file system delays
export TESTMON_XDIST_CHECK_INTERVAL=0.2
export TESTMON_XDIST_WORKER_TIMEOUT=60
```

### Windows

```powershell
# PowerShell profile
$env:TESTMON_XDIST_CONTROLLER_PRECREATION = "true"

# Handle Windows file locking
$env:TESTMON_XDIST_CHECK_INTERVAL = "0.3"
$env:TESTMON_XDIST_BACKOFF_FACTOR = "2.0"
```

### Linux (High-Performance)

```bash
# /etc/environment or ~/.bashrc
TESTMON_XDIST_CONTROLLER_PRECREATION=true

# Optimize for fast local SSD
TESTMON_XDIST_CHECK_INTERVAL=0.01    # 10ms
TESTMON_XDIST_BACKOFF_FACTOR=1.1    # Minimal backoff
TESTMON_XDIST_WORKER_TIMEOUT=10     # Fast timeout
```

## Troubleshooting Configurations

### Slow Network Filesystem

```bash
# For NFS, CIFS, or other network filesystems
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_CHECK_INTERVAL=1.0      # 1 second
export TESTMON_XDIST_BACKOFF_FACTOR=2.0      # Double each time
export TESTMON_XDIST_MAX_INTERVAL=10.0       # 10 seconds max
export TESTMON_XDIST_WORKER_TIMEOUT=300      # 5 minutes
```

### Limited Resources

```bash
# For systems with limited CPU/memory
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_WORKER_TIMEOUT=120

# Use fewer workers
pytest --testmon -n 2  # Instead of -n auto
```

### Debugging Failures

```bash
# When tests fail only with coordination
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
export TESTMON_XDIST_DEBUG=true

# Run with single worker first
pytest --testmon -n 1 -v

# Then try with multiple workers
pytest --testmon -n 2 -v

# Compare outputs
```