# Phase 3 Preview: Pytest Hook Integration

## Overview
With Phase 1 (coordination infrastructure) and Phase 2 (controller/worker logic) complete, Phase 3 will integrate everything with pytest hooks to actually fix the xdist readonly database issue.

## Key Integration Points

### 1. Modify `pytest_testmon.py`
```python
# In pytest_configure or pytest_sessionstart
if get_running_as(config) == "controller":
    # Initialize controller pre-creation
    controller_state = get_controller_state()
    controller_state.initialize(testmon_data, num_workers)
    
elif get_running_as(config) == "worker":
    # Initialize worker coordination
    worker_state = initialize_worker(worker_id, config)
    # Use pre-created environment instead of creating new
```

### 2. Add Readonly Checks to `db.py`
Implement the immediate fix by adding checks before write operations:
```python
def fetch_or_create_environment(self, ...):
    if self._readonly:
        # Return existing environment instead of creating
        return self._fetch_existing_environment(...)
    # ... existing create logic
```

### 3. Enhance `TestmonData` initialization
- Controller: Normal initialization with pre-creation
- Worker: Use coordinated initialization with pre-created IDs

### 4. Cleanup Integration
```python
def pytest_sessionfinish(session):
    # Clean up coordination files
    if get_running_as(config) == "controller":
        controller_state = get_controller_state()
        controller_state.cleanup()
```

## Testing Strategy

1. **Integration tests with real xdist**
   - Create test suite that triggers the issue
   - Run with coordination enabled
   - Verify no readonly errors

2. **Performance benchmarks**
   - Measure overhead of coordination
   - Ensure <5% impact on startup

3. **Backward compatibility**
   - Test without xdist
   - Test with feature flag disabled
   - Test mixed scenarios

## Expected Outcome

When complete, users will be able to:
```bash
# Enable the feature
export TESTMON_XDIST_CONTROLLER_PRECREATION=true

# Run tests with xdist - no more readonly errors!
pytest --testmon -n 4

# Everything just works™
```

## Implementation Steps

1. Start with minimal hook integration
2. Add readonly checks to critical db.py methods
3. Test with simple xdist scenario
4. Expand to cover all edge cases
5. Add performance optimizations

The foundation from Phases 1 & 2 makes this integration straightforward!