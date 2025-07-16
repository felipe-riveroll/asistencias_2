# Design Document

## Overview

The current attendance report script suffers from a classic N+1 query problem, where it makes individual database calls for each employee-day combination. This design document outlines a comprehensive optimization strategy that will reduce database queries from potentially thousands to just a few batch operations, while maintaining data accuracy and improving maintainability.

The optimization approach focuses on three main strategies:
1. **Batch Data Retrieval**: Replace individual queries with bulk operations
2. **In-Memory Caching**: Cache employee schedule data for reuse across date calculations
3. **Efficient Data Processing**: Pre-process and organize data structures for optimal lookup performance

## Architecture

### Current Architecture Problems
- Individual database query per employee-day combination (N×D queries where N=employees, D=days)
- Repeated database connections and disconnections
- No data reuse between similar schedule lookups
- Processing logic tightly coupled with database access

### Optimized Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   API Data      │     │  Batch DB Query  │     │  Data Processing│
│   Collection    │───▶│   & Caching      │───▶ │   & Analysis    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Schedule Cache  │
                       │  - Employee Data │
                       │  - Schedule Rules│
                       │  - Lookup Tables │
                       └──────────────────┘
```

## Components and Interfaces

### 1. ScheduleDataManager
**Purpose**: Centralized manager for all database operations and caching

**Key Methods**:
- `load_all_employee_schedules(employee_codes: List[str]) -> Dict`
- `get_schedule_for_employee_date(employee_code: str, date: datetime) -> Dict`
- `clear_cache()`

**Responsibilities**:
- Execute batch database queries
- Manage in-memory cache of schedule data
- Provide efficient lookup interface for schedule information

### 2. BatchQueryBuilder
**Purpose**: Construct optimized SQL queries for bulk data retrieval

**Key Methods**:
- `build_employee_schedule_query(employee_codes: List[str]) -> str`
- `build_schedule_rules_query() -> str`

**Responsibilities**:
- Generate SQL for fetching all employee schedule assignments
- Create queries that minimize database round-trips
- Handle complex JOIN operations efficiently

### 3. ScheduleCache
**Purpose**: In-memory storage and lookup for schedule data

**Data Structures**:
```python
{
    'employees': {
        'employee_code': {
            'schedule_assignments': [...],
            'default_schedule': {...},
            'special_dates': {...}
        }
    },
    'schedule_rules': {
        'schedule_id': {
            'entrada': '08:00:00',
            'salida': '17:00:00',
            'cruza_medianoche': False
        }
    },
    'turn_types': {
        'turn_id': {
            'descripcion': 'L-V',
            'days_pattern': [1,2,3,4,5]
        }
    }
}
```

### 4. OptimizedScheduleProcessor
**Purpose**: Process schedule data using cached information

**Key Methods**:
- `process_employee_schedules(df: pd.DataFrame) -> pd.DataFrame`
- `calculate_schedule_for_date(employee_code: str, date: datetime) -> Dict`

## Data Models

### Employee Schedule Data Model
```python
@dataclass
class EmployeeSchedule:
    employee_code: str
    schedule_assignments: List[ScheduleAssignment]
    has_assigned_schedule: bool
    
@dataclass
class ScheduleAssignment:
    schedule_id: Optional[int]
    turn_type_id: Optional[int]
    specific_day_id: Optional[int]
    is_first_fortnight: Optional[bool]
    priority: int
    
@dataclass
class ScheduleRule:
    entrada_time: str
    salida_time: str
    cruza_medianoche: bool
    turn_description: Optional[str]
```

### Cache Data Structure
The cache will be organized as nested dictionaries for O(1) lookup performance:
- Employee-level cache for schedule assignments
- Schedule rule cache for time calculations
- Turn type cache for day pattern matching

## Error Handling

### Database Connection Failures
- Implement connection pooling with retry logic
- Graceful degradation when database is unavailable
- Clear error messages indicating which employees couldn't be processed

### Partial Data Scenarios
- Continue processing with available data when some queries fail
- Log missing employee schedule information
- Provide summary of processing completeness

### Cache Consistency
- Implement cache invalidation strategies
- Handle memory constraints for large employee datasets
- Provide cache statistics and health monitoring

## Testing Strategy

### Unit Tests
- Test individual components (ScheduleDataManager, BatchQueryBuilder, ScheduleCache)
- Mock database connections for isolated testing
- Verify cache behavior and data consistency

### Integration Tests
- Test complete optimization pipeline with real database
- Compare results with original implementation for accuracy
- Performance benchmarking with various data sizes

### Performance Tests
- Measure query count reduction (target: 90% reduction)
- Benchmark execution time improvements
- Memory usage analysis for caching strategy

### Data Accuracy Tests
- Validate that optimized results match original output exactly
- Test edge cases (midnight crossing, special schedules, holidays)
- Verify schedule rule priority logic

## Implementation Strategy

### Phase 1: Batch Query Implementation
1. Create BatchQueryBuilder to generate optimized SQL
2. Implement ScheduleDataManager with batch loading
3. Replace individual queries with batch operations

### Phase 2: Caching Layer
1. Implement ScheduleCache with efficient data structures
2. Add cache population from batch query results
3. Create lookup methods for schedule resolution

### Phase 3: Processing Optimization
1. Refactor schedule processing to use cached data
2. Implement OptimizedScheduleProcessor
3. Update main analysis function to use new components

### Phase 4: Testing and Validation
1. Comprehensive testing suite
2. Performance benchmarking
3. Data accuracy validation

## Performance Expectations

### Query Reduction
- **Current**: N×D individual queries (e.g., 50 employees × 15 days = 750 queries)
- **Optimized**: 3-5 batch queries total (90%+ reduction)

### Execution Time
- **Target**: Complete processing in under 30 seconds for typical workloads
- **Memory Usage**: Reasonable cache size (estimated 1-10MB for typical datasets)

### Scalability
- Linear performance scaling with employee count
- Efficient handling of extended date ranges
- Minimal impact from database latency due to reduced round-trips