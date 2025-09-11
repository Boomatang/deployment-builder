# Plan: Directory-Based Configuration System

## Overview

This plan outlines the implementation of a directory-based configuration system that allows users to organize configuration files into a main `config.toml` file and a `config.d/` directory containing multiple smaller configuration files. This feature will be additive to the existing single-file configuration support.

## Problem Statement

Currently, users must maintain all configuration in a single file, which can become unwieldy for complex deployments. A directory-based approach would allow:

- Better organization of configuration by concern (clusters, services, etc.)
- Easier maintenance of large configurations
- Modular configuration management
- Better collaboration on configuration files

## Current State Analysis

### Existing Configuration System
- Single file configuration support (TOML, JSON, YAML)
- `DeploymentConfig` dataclass for type-safe configuration
- Configuration validation and error handling
- CLI `--config` flag for specifying configuration file

### Integration Points
- **Dynamic Cluster Types Plan**: No overlap - directory config will work with dynamic cluster types
- **Service Queue System Plan**: No overlap - directory config will work with service queue system
- **Existing CLI**: Extends `--config` flag to accept directories
- **Configuration Loading**: Extends existing config loading logic

## Proposed Solution

### Core Concept

Extend the existing configuration system to support directory-based configuration where:
- Main configuration file: `config.toml` (or `config.json`/`config.yaml`)
- Additional configuration files: `config.d/*.{toml,json,yaml}`
- Files processed in numeric prefix order (e.g., `01-base.toml`, `02-services.toml`)
- Last file wins for conflicts
- All formats supported (TOML, JSON, YAML)
- Final merged configuration validated as single unit

### Directory Structure

```
project/
├── config.toml              # Main configuration file
└── config.d/                # Additional configuration files
    ├── 01-base.toml         # Base settings
    ├── 02-clusters.toml     # Cluster definitions
    ├── 03-services.toml     # Service definitions
    ├── 04-monitoring.yaml   # Monitoring configuration
    └── 99-overrides.json    # Final overrides
```

### Configuration Merging Strategy

1. **Load Main Config**: Load the main configuration file
2. **Discover Files**: Find all files in `config.d/` directory
3. **Sort by Prefix**: Sort files by numeric prefix (e.g., `01-`, `02-`, etc.)
4. **Merge Sequentially**: Apply each file in order, with later files overriding earlier ones
5. **Validate Final**: Validate the merged configuration as a single unit

## Implementation Plan

### Phase 1: Core Directory Configuration Support

#### 1.1 Directory Discovery (`src/deployment_builder/config_loader.py`)

**New File: `src/deployment_builder/config_loader.py`**

```python
from pathlib import Path
from typing import Dict, List, Union, Any
import tomli
import json
import yaml
from .config import DeploymentConfig

class ConfigLoader:
    def __init__(self):
        self.supported_formats = {'.toml', '.json', '.yaml', '.yml'}
    
    def load_config(self, config_path: Union[str, Path]) -> DeploymentConfig:
        """Load configuration from file or directory."""
        config_path = Path(config_path)
        
        if config_path.is_file():
            return self._load_single_file(config_path)
        elif config_path.is_dir():
            return self._load_directory_config(config_path)
        else:
            raise ValueError(f"Config path must be a file or directory: {config_path}")
    
    def _load_single_file(self, file_path: Path) -> DeploymentConfig:
        """Load configuration from a single file."""
        # Existing single-file logic
    
    def _load_directory_config(self, dir_path: Path) -> DeploymentConfig:
        """Load configuration from directory structure."""
        # Main config file
        main_config = self._find_main_config(dir_path)
        if not main_config:
            raise ValueError(f"No main config file found in {dir_path}")
        
        # Load main config
        config_data = self._load_file(main_config)
        
        # Load and merge config.d files
        config_d_dir = dir_path / "config.d"
        if config_d_dir.exists():
            config_data = self._merge_config_files(config_data, config_d_dir)
        
        # Validate and return
        return self._validate_config(config_data)
    
    def _find_main_config(self, dir_path: Path) -> Optional[Path]:
        """Find main configuration file in directory."""
        for ext in ['.toml', '.json', '.yaml', '.yml']:
            config_file = dir_path / f"config{ext}"
            if config_file.exists():
                return config_file
        return None
    
    def _merge_config_files(self, base_config: Dict[str, Any], config_d_dir: Path) -> Dict[str, Any]:
        """Merge configuration files from config.d directory."""
        # Get all config files
        config_files = self._get_config_files(config_d_dir)
        
        # Sort by numeric prefix
        config_files.sort(key=self._get_sort_key)
        
        # Merge each file
        merged_config = base_config.copy()
        for config_file in config_files:
            file_config = self._load_file(config_file)
            merged_config = self._deep_merge(merged_config, file_config)
        
        return merged_config
    
    def _get_config_files(self, config_d_dir: Path) -> List[Path]:
        """Get all configuration files from config.d directory."""
        config_files = []
        for file_path in config_d_dir.iterdir():
            if file_path.is_file() and file_path.suffix in self.supported_formats:
                config_files.append(file_path)
        return config_files
    
    def _get_sort_key(self, file_path: Path) -> tuple:
        """Get sort key for file ordering (numeric prefix)."""
        filename = file_path.stem
        if filename[0].isdigit():
            # Extract numeric prefix
            prefix = ""
            for char in filename:
                if char.isdigit():
                    prefix += char
                else:
                    break
            return (int(prefix) if prefix else 999, filename)
        return (999, filename)  # Files without numeric prefix go last
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
```

#### 1.2 Update CLI Integration

**Update `src/deployment_builder/cli.py`:**

```python
from .config_loader import ConfigLoader

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file or directory path')
def create(config):
    """Create clusters and deploy services."""
    try:
        # Load configuration using new loader
        loader = ConfigLoader()
        deployment_config = loader.load_config(config)
        
        # Rest of existing logic...
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Abort()
```

#### 1.3 Update Configuration Module

**Update `src/deployment_builder/config.py`:**

```python
# Add helper function for backward compatibility
def load_config_from_path(config_path: Union[str, Path]) -> DeploymentConfig:
    """Load configuration from file or directory path."""
    loader = ConfigLoader()
    return loader.load_config(config_path)
```

### Phase 2: Enhanced Error Handling and Validation

#### 2.1 Detailed Error Messages

**Enhanced Error Handling:**

```python
class ConfigLoadError(Exception):
    """Configuration loading error with detailed information."""
    def __init__(self, message: str, file_path: Optional[Path] = None, line_number: Optional[int] = None):
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        msg = self.message
        if self.file_path:
            msg += f" in {self.file_path}"
        if self.line_number:
            msg += f" at line {self.line_number}"
        return msg
```

#### 2.2 Configuration Validation

**Enhanced Validation:**

```python
def _validate_config(self, config_data: Dict[str, Any]) -> DeploymentConfig:
    """Validate merged configuration data."""
    try:
        # Validate using existing DeploymentConfig validation
        return DeploymentConfig.from_dict(config_data)
    except Exception as e:
        raise ConfigLoadError(f"Configuration validation failed: {e}")
```

### Phase 3: Testing

#### 3.1 Unit Tests (`tests/test_config_loader.py`)

**Test File Structure:**

```python
import pytest
from pathlib import Path
from deployment_builder.config_loader import ConfigLoader, ConfigLoadError

class TestConfigLoader:
    def test_load_single_file(self, tmp_path):
        """Test loading single configuration file."""
        
    def test_load_directory_config(self, tmp_path):
        """Test loading directory-based configuration."""
        
    def test_file_ordering(self, tmp_path):
        """Test that files are processed in correct order."""
        
    def test_config_merging(self, tmp_path):
        """Test configuration merging with last-file-wins."""
        
    def test_format_support(self, tmp_path):
        """Test support for all configuration formats."""
        
    def test_error_handling(self, tmp_path):
        """Test error handling for invalid configurations."""
        
    def test_missing_main_config(self, tmp_path):
        """Test error when main config file is missing."""
        
    def test_empty_config_d(self, tmp_path):
        """Test handling of empty config.d directory."""
```

#### 3.2 Integration Tests

**Update `tests/test_cli_integration.py`:**

```python
def test_create_with_directory_config(cli_runner, tmp_path):
    """Test create command with directory-based configuration."""
    
def test_create_with_mixed_formats(cli_runner, tmp_path):
    """Test create command with mixed configuration formats."""
```

### Phase 4: Documentation and Examples

#### 4.1 Documentation Updates

**Update `README.md`:**

```markdown
## Configuration

### Single File Configuration
```bash
poetry run deploy create --config config.toml
```

### Directory-Based Configuration
```bash
poetry run deploy create --config /path/to/config/directory
```

#### Directory Structure
```
config/
├── config.toml              # Main configuration
└── config.d/                # Additional configuration files
    ├── 01-base.toml         # Base settings
    ├── 02-clusters.toml     # Cluster definitions
    ├── 03-services.toml     # Service definitions
    └── 99-overrides.json    # Final overrides
```

#### File Processing Order
Files in `config.d/` are processed in numeric prefix order:
- `01-base.toml` (processed first)
- `02-clusters.toml`
- `03-services.toml`
- `99-overrides.json` (processed last, overrides previous)

#### Configuration Merging
- Later files override earlier files for conflicting keys
- Deep merging for nested objects
- Arrays are replaced entirely
```

#### 4.2 Example Configurations

**Create `examples/directory-config/`:**

```
examples/directory-config/
├── config.toml
└── config.d/
    ├── 01-base.toml
    ├── 02-clusters.toml
    ├── 03-services.toml
    └── 99-overrides.json
```

### Phase 5: Performance and Optimization

#### 5.1 Caching and Performance

**Configuration Caching:**

```python
class ConfigLoader:
    def __init__(self, cache_configs: bool = True):
        self.cache_configs = cache_configs
        self._cache: Dict[Path, DeploymentConfig] = {}
    
    def load_config(self, config_path: Union[str, Path]) -> DeploymentConfig:
        """Load configuration with optional caching."""
        config_path = Path(config_path).resolve()
        
        if self.cache_configs and config_path in self._cache:
            return self._cache[config_path]
        
        config = self._load_config_impl(config_path)
        
        if self.cache_configs:
            self._cache[config_path] = config
        
        return config
```

#### 5.2 Memory Optimization

**Lazy Loading:**

```python
def _load_file(self, file_path: Path) -> Dict[str, Any]:
    """Load configuration file with memory optimization."""
    # Use streaming for large files if needed
    # Implement file format detection
    # Optimize memory usage for large configurations
```

## Implementation Timeline

### Week 1: Core Implementation
- [ ] Implement `ConfigLoader` class
- [ ] Add directory discovery and file sorting
- [ ] Implement configuration merging logic
- [ ] Update CLI integration

### Week 2: Testing and Validation
- [ ] Write comprehensive unit tests
- [ ] Add integration tests
- [ ] Test error handling scenarios
- [ ] Validate with existing test suite

### Week 3: Documentation and Examples
- [ ] Update README.md
- [ ] Create example directory configurations
- [ ] Add usage documentation
- [ ] Create migration guide

### Week 4: Performance and Polish
- [ ] Implement configuration caching
- [ ] Optimize memory usage
- [ ] Performance testing
- [ ] Final integration testing

## Risk Assessment

### Low Risk
- **Backward Compatibility**: Additive feature, existing functionality unchanged
- **Integration**: No overlap with existing plans
- **Testing**: Well-defined test cases

### Medium Risk
- **Configuration Merging**: Complex logic for deep merging
- **File Ordering**: Numeric prefix parsing edge cases
- **Error Handling**: Complex error reporting across multiple files

### High Risk
- **Performance**: Large configurations with many files
- **Memory Usage**: Loading multiple configuration files

## Mitigation Strategies

### Configuration Merging
- Comprehensive test cases for merging scenarios
- Clear documentation of merging behavior
- Validation of merged configuration

### File Ordering
- Robust numeric prefix parsing
- Fallback to alphabetical ordering
- Clear error messages for invalid prefixes

### Performance
- Configuration caching
- Lazy loading for large files
- Memory usage monitoring

## Success Criteria

### Functional Requirements
- [ ] Directory-based configuration loading
- [ ] Support for all configuration formats
- [ ] Proper file ordering and merging
- [ ] Backward compatibility maintained
- [ ] Comprehensive error handling

### Performance Requirements
- [ ] No significant performance degradation
- [ ] Efficient memory usage
- [ ] Fast configuration loading

### Usability Requirements
- [ ] Clear documentation and examples
- [ ] Intuitive directory structure
- [ ] Helpful error messages

## Future Enhancements

### Phase 2 Features
- **Nested Directories**: Support for `config.d/services/`, `config.d/clusters/`
- **Configuration Templates**: Template system for common configurations
- **Configuration Validation**: Per-file validation with detailed error reporting
- **Configuration Diff**: Show differences between configurations

### Advanced Features
- **Configuration Inheritance**: Base configuration inheritance
- **Environment-Specific Configs**: Environment-based configuration selection
- **Configuration Encryption**: Encrypted configuration files
- **Remote Configuration**: Load configuration from remote sources

## Conclusion

The directory-based configuration system will significantly improve the usability and maintainability of complex deployments while maintaining full backward compatibility. The implementation is straightforward and integrates well with existing plans for dynamic cluster types and service queue systems.

The phased approach ensures robust implementation with comprehensive testing and documentation, providing users with a powerful and flexible configuration management system.
