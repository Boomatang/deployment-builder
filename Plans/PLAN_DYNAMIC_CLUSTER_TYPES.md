# Plan: Dynamic Cluster Types Configuration

## Problem Statement

The current deployment-builder system hardcodes four specific cluster types: `metrics`, `primary`, `secondary`, and `standalone`. This is a bad assumption that limits user flexibility. Users should be able to define any cluster types they need for their specific use cases.

## Current State Analysis

### Hardcoded Cluster Types
The system currently assumes these four cluster types:
- `metrics` - Single cluster (enable: true/false)
- `primary` - Multiple clusters (count: number)
- `secondary` - Multiple clusters (count: number)  
- `standalone` - Multiple clusters (count: number)

### Current Implementation Points
1. **Configuration Object** (`src/deployment_builder/config.py`):
   - `DeploymentConfig.clusters` hardcodes the four types in `default_factory`
   - `get_cluster_names()` method hardcodes cluster type logic
   - `update_from_dict()` method expects specific cluster types

2. **Kind Integration** (`src/deployment_builder/kind_integration.py`):
   - `get_cluster_names_from_config()` hardcodes cluster type processing
   - `_get_cluster_type_from_name()` hardcodes known cluster types
   - Both new and legacy format processing hardcodes types

3. **Tests** (`tests/`):
   - All tests assume the four hardcoded cluster types
   - Test data and assertions hardcode specific cluster names
   - Example configurations use hardcoded types

4. **Documentation** (`README.md`):
   - Documentation describes specific cluster types
   - Examples show hardcoded cluster types
   - Configuration sections reference specific types

## Proposed Solution

### Core Concept
Replace hardcoded cluster types with a dynamic system where:
- Users can define any cluster types they need
- Each cluster type can be configured as single (enable: true/false) or multiple (count: number)
- The system dynamically processes any cluster types defined in configuration
- Clean, modern configuration format without legacy baggage

### New Configuration Format

#### Dynamic Cluster Types Format
```toml
[general]
name = "my-deployment"
prefix = "my-project"

[clusters]
# Single cluster types (enable: true/false)
[clusters.metrics]
enable = true

[clusters.gateway]
enable = true

# Multiple cluster types (count: number)
[clusters.primary]
count = 2

[clusters.worker]
count = 3

[clusters.database]
count = 1

[clusters.cache]
count = 2
```

## Implementation Plan

### Phase 1: Core Configuration System Changes

#### 1.1 Update Configuration Object (`src/deployment_builder/config.py`)

**Changes Required:**
- Remove hardcoded cluster types from `DeploymentConfig.clusters` default factory
- Make `clusters` field dynamically populated from configuration
- Update `get_cluster_names()` method to process any cluster types
- Update `update_from_dict()` method to handle dynamic cluster types
- Add validation for cluster type names (alphanumeric, hyphens, underscores)

**Key Functions to Modify:**
```python
@dataclass
class DeploymentConfig:
    # Change from hardcoded to dynamic
    clusters: Dict[str, ClusterConfig] = field(default_factory=dict)
    
    def get_cluster_names(self) -> list[str]:
        # Process any cluster types dynamically
        
    def update_from_dict(self, config_data: Dict[str, Any]) -> None:
        # Handle dynamic cluster types
```

**Validation Rules:**
- Cluster type names must be valid identifiers (alphanumeric, hyphens, underscores)
- Cluster type names must not conflict with reserved words
- Maximum cluster type name length: 50 characters
- Minimum cluster type name length: 1 character

#### 1.2 Update Kind Integration (`src/deployment_builder/kind_integration.py`)

**Changes Required:**
- Update `get_cluster_names_from_config()` to process any cluster types
- Update `_get_cluster_type_from_name()` to work with dynamic types
- Remove hardcoded cluster type logic
- Add cluster type validation

**Key Functions to Modify:**
```python
def get_cluster_names_from_config(config_data: dict) -> list[str]:
    # Process any cluster types from configuration
    
def _get_cluster_type_from_name(cluster_name: str) -> Optional[str]:
    # Extract cluster type from any cluster name pattern
```

**Algorithm Changes:**
- Parse cluster configuration dynamically
- Support both single (enable) and multiple (count) cluster types
- Generate cluster names based on type and count
- Maintain backward compatibility with legacy format

### Phase 2: Service Configuration Updates

#### 2.1 Cluster-Specific Services

**Current Format:**
```toml
[clusters.primary.services]
[clusters.primary.services.namespaces]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get namespaces"
```

**New Dynamic Format:**
```toml
[clusters.worker.services]
[clusters.worker.services.monitoring]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n monitoring"

[clusters.database.services]
[clusters.database.services.backup]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pv"
```

**Changes Required:**
- Update service processing to work with any cluster type
- Validate cluster type references in service configuration
- Update service execution logic

### Phase 3: Configuration Validation and Error Handling

#### 3.1 Cluster Type Validation

**Validation Rules:**
- Cluster type names must be valid identifiers (alphanumeric, hyphens, underscores)
- Cluster type names must not conflict with reserved words
- Maximum cluster type name length: 50 characters
- Minimum cluster type name length: 1 character
- No duplicate cluster type names allowed

**Error Messages:**
```python
# Invalid cluster type name
"Invalid cluster type name 'my-cluster!': must contain only alphanumeric characters, hyphens, and underscores"

# Duplicate cluster type
"Duplicate cluster type 'worker' found in configuration"

# Invalid count value
"Invalid count value for cluster type 'worker': must be a positive integer"
```

#### 3.2 Configuration Schema Validation

**Schema Requirements:**
- Each cluster type must have either `enable` or `count` property
- `enable` must be boolean (true/false)
- `count` must be non-negative integer
- Cluster type names must be unique within configuration

### Phase 4: Testing Updates

#### 4.1 Test Data Updates

**Update Test Fixtures:**
- Create test data with custom cluster types
- Add tests for dynamic cluster type processing
- Test backward compatibility with legacy format
- Test edge cases (invalid cluster type names, etc.)

**New Test Cases:**
```python
def test_dynamic_cluster_types():
    """Test configuration with custom cluster types."""
    config_data = {
        "clusters": {
            "gateway": {"enable": True},
            "worker": {"count": 3},
            "database": {"count": 1},
        }
    }
    # Test cluster name generation

def test_cluster_type_validation():
    """Test cluster type name validation."""
    # Test invalid cluster type names
    # Test duplicate cluster type names
    # Test invalid count values

def test_single_vs_multiple_cluster_types():
    """Test both single and multiple cluster type configurations."""
    config_data = {
        "clusters": {
            "gateway": {"enable": True},  # Single
            "worker": {"count": 3},       # Multiple
        }
    }
    # Test mixed configuration
```

#### 4.2 Integration Tests

**Update Integration Tests:**
- Test CLI commands with custom cluster types
- Test kind integration with dynamic cluster types
- Test kubeconfig management with custom types
- Test service execution with custom cluster types
- Test configuration validation and error handling

### Phase 5: Documentation Updates

#### 5.1 README.md Updates

**New Configuration Section:**
```markdown
### Dynamic Cluster Types

The tool supports any cluster types you define:

```toml
[clusters]
# Single cluster types
[clusters.metrics]
enable = true

[clusters.gateway]
enable = true

# Multiple cluster types
[clusters.worker]
count = 3

[clusters.database]
count = 1
```

**Cluster Type Rules:**
- Names must be alphanumeric with hyphens and underscores
- Single clusters use `enable: true/false`
- Multiple clusters use `count: number`
- No limit on number of cluster types
```

#### 5.2 Example Configurations

**Create New Examples:**
- `examples/dynamic-clusters.toml` - Custom cluster types
- `examples/microservices.toml` - Microservices architecture
- `examples/edge-computing.toml` - Edge computing setup

#### 5.3 Best Practices Guide

**Document Best Practices:**
- Cluster type naming conventions
- When to use single vs multiple cluster types
- Configuration organization tips
- Performance considerations for many cluster types

### Phase 6: Documentation Updates

#### 6.1 README.md Updates

**Update Help Text:**
- Document dynamic cluster types in help
- Show examples of custom cluster types
- Explain cluster type naming rules

### Phase 7: Final Testing and Validation

#### 7.1 Comprehensive Testing

**Test Coverage:**
- All cluster type combinations
- Edge cases and error conditions
- Performance with many cluster types
- Integration with all system components

#### 7.2 User Acceptance Testing

**Validation:**
- Real-world configuration scenarios
- User workflow testing
- Documentation accuracy
- Error message clarity

## Implementation Timeline

### Week 1: Core Configuration Changes
- Update `DeploymentConfig` class
- Implement dynamic cluster type processing
- Add validation and error handling

### Week 2: Kind Integration Updates
- Update `get_cluster_names_from_config()`
- Update `_get_cluster_type_from_name()`
- Test cluster name generation

### Week 3: Service Configuration Updates
- Update service processing for dynamic cluster types
- Test cluster-specific services
- Update service execution logic

### Week 4: Configuration Validation
- Implement cluster type validation
- Add comprehensive error handling
- Test validation scenarios

### Week 5: Testing and Documentation
- Update all tests
- Create new test cases
- Update documentation
- Create example configurations

### Week 6: Final Testing and Validation
- Comprehensive testing
- Performance optimization
- Final validation and user acceptance testing

## Risk Assessment

### High Risk
- **Complexity**: Dynamic processing adds complexity
- **Testing**: Extensive testing required for all scenarios
- **Configuration Validation**: Complex validation logic needed

### Medium Risk
- **Performance**: Dynamic processing may impact performance
- **Memory Usage**: Additional memory for dynamic cluster types
- **Documentation**: Extensive documentation updates needed

### Low Risk
- **User Adoption**: Users may need time to adapt to new format
- **Error Handling**: Complex error scenarios to handle

## Mitigation Strategies

### Complexity
- Comprehensive testing
- Clear documentation
- Code review and refactoring
- Incremental implementation

### Performance
- Performance testing
- Optimization where needed
- Caching strategies
- Memory usage monitoring

### Configuration Validation
- Clear error messages
- Helpful validation feedback
- Comprehensive test coverage
- User-friendly documentation

## Success Criteria

### Functional Requirements
- [ ] Users can define any cluster types they need
- [ ] Single and multiple cluster types supported
- [ ] Clean, modern configuration format
- [ ] All existing functionality preserved

### Non-Functional Requirements
- [ ] Performance maintained or improved
- [ ] Memory usage reasonable
- [ ] Clear error messages
- [ ] Comprehensive documentation

### Quality Requirements
- [ ] All tests pass
- [ ] Code coverage maintained
- [ ] Clean, maintainable code
- [ ] User-friendly error messages

## Future Enhancements

### Advanced Features
- Cluster type templates
- Cluster type inheritance
- Dynamic cluster type validation
- Cluster type metadata

### Integration Features
- Cluster type discovery
- Automatic cluster type suggestions
- Cluster type best practices
- Integration with external systems

## Conclusion

This plan provides a comprehensive approach to making cluster types configurable with a clean, modern implementation. Since the project is in early stages, we can implement the optimal solution without legacy compatibility constraints.

The key benefits of this implementation:
1. **Flexibility**: Users can define any cluster types they need
2. **Scalability**: No limit on number of cluster types
3. **Simplicity**: Clean, modern configuration format
4. **Usability**: Clear error messages and helpful documentation
5. **Maintainability**: Clean, well-tested code without legacy baggage

This change will significantly improve the tool's flexibility and make it suitable for a wider range of use cases while maintaining clean, maintainable code. The absence of legacy compatibility requirements allows for a more elegant and efficient implementation.
