# Controller Pre-creation Implementation Plan

## Overview
Implement a controller pre-creation strategy to fix the xdist readonly database issue in pytest-testmon. This solution ensures that the controller process creates all necessary database entries before workers begin execution, allowing workers to operate in true readonly mode.

## Goals
1. **Fix the immediate issue**: Prevent `sqlite3.OperationalError: attempt to write a readonly database`
2. **Maintain backward compatibility**: Ensure non-xdist usage continues to work
3. **High test coverage**: Comprehensive tests for all new functionality
4. **Safe iteration**: Implement in small, testable phases

## Implementation Phases

### Phase 1: Coordination Infrastructure (Week 1)
**Goal**: Create the foundation for controller-worker communication

1. **Create coordination module** (`testmon/xdist/coordination.py`)
   - File-based coordination system
   - JSON state serialization
   - Timeout and retry mechanisms

2. **Add configuration** (`testmon/xdist/config.py`)
   - Feature flags for gradual rollout
   - Configuration options
   - Logging setup

3. **Tests**:
   - Unit tests for coordination primitives
   - Integration tests for file-based communication
   - Error handling tests

### Phase 2: Controller Pre-creation Logic (Week 2)
**Goal**: Implement database pre-creation in the controller

1. **Controller hooks** (`testmon/xdist/controller.py`)
   - Pre-create environments
   - Scan for test files
   - Initialize database state

2. **Database enhancements**
   - Add batch creation methods
   - Optimize for pre-creation scenario
   - Add readonly mode enforcement

3. **Tests**:
   - Controller initialization tests
   - Database pre-creation tests
   - Performance tests

### Phase 3: Worker Synchronization (Week 3)
**Goal**: Implement worker-side coordination

1. **Worker hooks** (`testmon/xdist/worker.py`)
   - Wait for controller signal
   - Acknowledge readiness
   - Fallback mechanisms

2. **Integration with pytest hooks**
   - Modify `pytest_configure`
   - Enhance `pytest_sessionstart`
   - Add cleanup in `pytest_sessionfinish`

3. **Tests**:
   - Worker synchronization tests
   - Timeout handling tests
   - Multi-worker scenario tests

### Phase 4: Comprehensive Testing (Week 4)
**Goal**: Ensure robustness with high test coverage

1. **End-to-end tests**
   - Full xdist execution tests
   - Failure scenario tests
   - Performance benchmarks

2. **Backward compatibility tests**
   - Non-xdist execution
   - Mixed mode scenarios
   - Version compatibility

3. **Stress tests**
   - Many workers (10+)
   - Large test suites
   - Network/filesystem issues

### Phase 5: Integration & Polish (Week 5)
**Goal**: Final integration and documentation

1. **Integration**
   - Merge with main testmon code
   - Feature flag configuration
   - Gradual rollout plan

2. **Documentation**
   - User documentation
   - Migration guide
   - Troubleshooting guide

3. **Monitoring**
   - Performance metrics
   - Error tracking
   - Usage analytics

## Risk Mitigation

### Backward Compatibility
- All new functionality behind feature flags
- Extensive testing of existing functionality
- Gradual rollout with monitoring

### Performance
- Benchmark all changes
- Optimize critical paths
- Add caching where appropriate

### Error Handling
- Graceful fallbacks at every level
- Clear error messages
- Recovery mechanisms

## Success Criteria

1. **Functional**
   - No more readonly database errors with xdist
   - All existing tests pass
   - New tests provide >90% coverage

2. **Performance**
   - No significant slowdown for non-xdist usage
   - <5% overhead for xdist initialization
   - Scales linearly with worker count

3. **Reliability**
   - Handles all failure scenarios gracefully
   - No data corruption or loss
   - Clear error messages for debugging

## Rollout Strategy

1. **Alpha** (Internal testing)
   - Feature flag enabled for specific projects
   - Collect metrics and feedback
   - Fix any critical issues

2. **Beta** (Opt-in)
   - Document feature flag
   - Enable for interested users
   - Monitor error rates

3. **GA** (General Availability)
   - Enable by default
   - Keep feature flag for rollback
   - Full documentation

## Timeline

- **Week 1**: Phase 1 - Coordination Infrastructure
- **Week 2**: Phase 2 - Controller Pre-creation
- **Week 3**: Phase 3 - Worker Synchronization
- **Week 4**: Phase 4 - Comprehensive Testing
- **Week 5**: Phase 5 - Integration & Polish
- **Week 6**: Alpha rollout
- **Week 7-8**: Beta period
- **Week 9**: GA release

## Code Structure

```
testmon/
├── xdist/
│   ├── __init__.py          # Module initialization
│   ├── coordination.py      # Coordination primitives
│   ├── config.py           # Configuration and feature flags
│   ├── controller.py       # Controller-side logic
│   ├── worker.py          # Worker-side logic
│   └── exceptions.py      # Custom exceptions
├── pytest_testmon.py      # Integration points
└── db.py                  # Enhanced with batch operations
```

## Next Steps

1. Create the basic module structure
2. Implement Phase 1 coordination infrastructure
3. Write comprehensive tests for Phase 1
4. Review and iterate before moving to Phase 2