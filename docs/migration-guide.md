# Migration Guide: Enabling xdist Coordination

This guide helps you migrate from experiencing readonly database errors to using the new xdist coordination feature.

## Before Migration

If you're currently experiencing this error:
```
INTERNALERROR> sqlite3.OperationalError: attempt to write a readonly database
```

When running:
```bash
pytest --testmon -n 4  # or any -n value > 1
```

## Migration Steps

### Step 1: Verify Current Setup

Check your current versions:
```bash
pytest --version
pytest --testmon --version
pytest -n 1 --version  # pytest-xdist version
```

Ensure you have:
- pytest >= 6.0
- pytest-testmon >= 2.0
- pytest-xdist >= 2.0

### Step 2: Test Without Changes

First, verify the issue exists:
```bash
# This likely shows the readonly error
pytest --testmon -n 4 tests/
```

### Step 3: Enable Coordination

Set the environment variable:
```bash
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
```

### Step 4: Run Tests

```bash
# Same command, but now it works!
pytest --testmon -n 4 tests/
```

### Step 5: Verify Success

You should see:
- No `sqlite3.OperationalError` errors
- Tests running in parallel
- Normal test output

## Integration Strategies

### Local Development

Add to your shell configuration (`~/.bashrc`, `~/.zshrc`, etc.):
```bash
# Enable testmon xdist coordination
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
```

### Team Development

Create a project script (`scripts/test.sh`):
```bash
#!/bin/bash
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
pytest --testmon -n auto "$@"
```

### CI/CD Systems

#### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -e .[test]
      - run: pytest --testmon -n auto
        env:
          TESTMON_XDIST_CONTROLLER_PRECREATION: true
```

#### GitLab CI
```yaml
test:
  script:
    - pip install -e .[test]
    - pytest --testmon -n auto
  variables:
    TESTMON_XDIST_CONTROLLER_PRECREATION: "true"
```

#### Jenkins
```groovy
pipeline {
    agent any
    environment {
        TESTMON_XDIST_CONTROLLER_PRECREATION = 'true'
    }
    stages {
        stage('Test') {
            steps {
                sh 'pip install -e .[test]'
                sh 'pytest --testmon -n auto'
            }
        }
    }
}
```

#### CircleCI
```yaml
version: 2.1
jobs:
  test:
    docker:
      - image: cimg/python:3.9
    environment:
      TESTMON_XDIST_CONTROLLER_PRECREATION: true
    steps:
      - checkout
      - run: pip install -e .[test]
      - run: pytest --testmon -n auto
```

## Rollback Plan

If you encounter issues, disable the feature instantly:

```bash
# Disable coordination
unset TESTMON_XDIST_CONTROLLER_PRECREATION
# or
export TESTMON_XDIST_CONTROLLER_PRECREATION=false

# Run tests (will have readonly errors again)
pytest --testmon -n 4
```

## Common Migration Scenarios

### Scenario 1: Intermittent Errors

**Before:** Sometimes get readonly errors, sometimes not  
**After:** Consistent success with coordination enabled

### Scenario 2: Workaround with Single Process

**Before:**
```bash
# Avoided error by not using -n
pytest --testmon
```

**After:**
```bash
# Can now use parallel execution
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
pytest --testmon -n auto  # Full parallelization!
```

### Scenario 3: Custom Database Location

**Before:**
```bash
export TESTMON_DATAFILE=/custom/path/.testmondata
pytest --testmon -n 4  # Readonly error
```

**After:**
```bash
export TESTMON_DATAFILE=/custom/path/.testmondata
export TESTMON_XDIST_CONTROLLER_PRECREATION=true
pytest --testmon -n 4  # Works!
```

## Verification Checklist

After migration, verify:

- [ ] No readonly database errors
- [ ] Tests run in parallel (check output shows multiple workers)
- [ ] Test selection still works (modified files trigger correct tests)
- [ ] Performance is acceptable (should be similar or better)
- [ ] CI/CD pipelines pass
- [ ] Team members can run tests locally

## Performance Comparison

Typical improvements after migration:

| Metric | Before | After |
|--------|--------|-------|
| Parallel execution | ❌ Disabled or errors | ✅ Full parallelization |
| Test runtime | Single process only | 2-8x faster with -n auto |
| Reliability | Intermittent failures | Consistent success |
| Setup complexity | Complex workarounds | Single env variable |

## Gradual Rollout

For large teams, consider gradual rollout:

### Week 1: Development Team
- Enable for local development
- Monitor for issues
- Collect feedback

### Week 2: CI/CD (Non-Critical)
- Enable for feature branches
- Monitor performance
- Verify no regressions

### Week 3: Production CI/CD
- Enable for main/master branch
- Full team adoption
- Document any issues

### Week 4: Make Default
- Update documentation
- Remove workarounds
- Celebrate! 🎉

## Troubleshooting Migration

### Issue: Still Getting Readonly Errors

Check:
1. Environment variable is set: `echo $TESTMON_XDIST_CONTROLLER_PRECREATION`
2. Using bash/zsh? Ensure exported: `export TESTMON_XDIST_CONTROLLER_PRECREATION=true`
3. CI system passing environment correctly

### Issue: Tests Slower Than Before

1. Check worker count: `-n auto` might choose too many
2. Try explicit count: `-n 4` or `-n 8`
3. Enable debug mode to see timing

### Issue: Coordination Timeout

Increase timeout for slow systems:
```bash
export TESTMON_XDIST_WORKER_TIMEOUT=60
```

## Need Help?

1. Enable debug mode: `export TESTMON_XDIST_DEBUG=true`
2. Check logs for coordination messages
3. Report issues with debug output

## Success Metrics

You'll know migration is successful when:
- Zero readonly database errors in 1 week
- Test execution time reduced by 50%+
- No custom workarounds needed
- Team productivity increased

Congratulations on migrating to parallel test execution! 🚀