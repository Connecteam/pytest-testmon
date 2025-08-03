# Phase 2 Preview: Controller Pre-creation Logic

## Overview
With Phase 1's coordination infrastructure complete, Phase 2 will implement the actual controller pre-creation logic that fixes the xdist readonly database issue.

## Key Components to Implement

### 1. Controller Module (`testmon/xdist_coordination/controller.py`)
```python
class ControllerPreCreation:
    """Handles database pre-creation for xdist controller."""
    
    def pre_create_environments(self, testmon_data):
        """Pre-create all necessary database entries."""
        # - Create current environment
        # - Scan for test files
        # - Pre-populate known data
        
    def prepare_for_workers(self, num_workers):
        """Prepare database state for worker processes."""
        # - Lock database for initial setup
        # - Create required entries
        # - Signal workers when ready
```

### 2. Worker Module (`testmon/xdist_coordination/worker.py`)
```python
class WorkerCoordination:
    """Handles worker-side coordination."""
    
    def wait_and_initialize(self, worker_id):
        """Wait for controller and initialize readonly access."""
        # - Wait for controller signal
        # - Initialize with readonly database
        # - Handle timeout/fallback
```

### 3. Database Enhancements
- Add batch creation methods to `testmon/db.py`
- Optimize for pre-creation scenarios
- Add better readonly enforcement

### 4. Integration Points
- Modify `pytest_configure` hook
- Enhance `pytest_sessionstart` 
- Add cleanup in `pytest_sessionfinish`

## Implementation Strategy

1. **Start with minimal integration**
   - Basic controller pre-creation
   - Simple worker waiting
   - Test with 2 workers

2. **Add robustness**
   - Error handling
   - Fallback mechanisms
   - Performance optimization

3. **Full integration**
   - All pytest hooks
   - Complete error scenarios
   - Performance benchmarks

## Testing Plan

1. **Unit tests** for controller/worker classes
2. **Integration tests** with real database
3. **End-to-end tests** with actual xdist execution
4. **Performance tests** to ensure minimal overhead

## Success Criteria

- ✅ No more readonly database errors
- ✅ Minimal startup overhead (<5%)
- ✅ Backward compatible
- ✅ Clear error messages
- ✅ 90%+ test coverage

## Next Session Goals

1. Create controller.py with basic pre-creation logic
2. Create worker.py with synchronization
3. Add initial pytest hook integration
4. Write comprehensive tests
5. Test with actual xdist execution

The foundation is solid, and Phase 2 will build upon it to deliver the complete solution!