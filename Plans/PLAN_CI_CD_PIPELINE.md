# Plan: CI/CD Pipeline for deployment-builder

## Overview

This plan outlines the implementation of a comprehensive CI/CD pipeline for the deployment-builder tool, including GitHub Actions workflows, pre-commit hooks, automated testing, PyPI distribution, and release management. The pipeline will ensure code quality, automated testing, and streamlined distribution.

## Problem Statement

Currently, the deployment-builder project lacks automated CI/CD processes, which means:
- No automated testing on code changes
- No code quality enforcement
- No automated distribution to PyPI
- No release management automation
- Manual dependency updates and security scanning
- No automated documentation generation

## Current State Analysis

### Existing Project Structure
- **Language**: Python 3.13+
- **Package Manager**: Poetry
- **Testing Framework**: pytest
- **Code Formatting**: Black (120 character line length)
- **Source Repository**: GitHub
- **Target Distribution**: PyPI (planned)
- **Entry Point**: `deployment_builder.cli:cli`

### Current Development Workflow
- Manual code formatting with `poetry run black`
- Manual testing with `poetry run pytest`
- Manual CLI testing with `poetry run deploy --help`
- No automated CI/CD processes

### Integration Points
- **Directory Configuration Plan**: CI/CD will validate new configuration formats
- **Service Queue System Plan**: CI/CD will test parallel processing features
- **Dynamic Cluster Types Plan**: CI/CD will validate dynamic cluster type configurations
- **Existing CLI**: CI/CD will test all CLI commands and options

## Proposed Solution

### Core Concept

Implement a comprehensive CI/CD pipeline using:
- **GitHub Actions** for CI/CD workflows
- **pre-commit** for local code quality enforcement
- **PyPI** for package distribution
- **Automated testing** with comprehensive coverage
- **Security scanning** and dependency updates
- **Release automation** with semantic versioning

### Pipeline Architecture

#### 1. Pre-commit Hooks (Local Development)
- Code formatting with Black
- Import sorting with isort
- Linting with flake8/ruff
- Type checking with mypy
- Security scanning with bandit
- Commit message validation

#### 2. GitHub Actions Workflows
- **Pull Request Workflow**: Code quality, testing, security
- **Main Branch Workflow**: Full testing, building, distribution
- **Release Workflow**: Automated PyPI publishing
- **Dependency Update Workflow**: Automated dependency updates
- **Security Workflow**: Security scanning and alerts

#### 3. PyPI Distribution
- Automated package building
- PyPI publishing on releases
- Test PyPI publishing for PR validation
- Package metadata validation

## Implementation Plan

### Phase 1: Pre-commit Setup

#### 1.1 Pre-commit Configuration (`.pre-commit-config.yaml`)

**New File: `.pre-commit-config.yaml`**

```yaml
repos:
  # Black code formatting
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
        language_version: python3.13
        args: [--line-length=120]

  # isort import sorting
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black, --line-length=120]

  # flake8 linting
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203,W503]

  # mypy type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-requests]
        args: [--ignore-missing-imports]

  # bandit security scanning
  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/, -f, json, -o, bandit-report.json]

  # commit message validation
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen

  # general hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
      - id: debug-statements
      - id: check-docstring-first
```

#### 1.2 Pre-commit Installation Script

**New File: `scripts/setup-pre-commit.sh`**

```bash
#!/bin/bash
# Setup pre-commit hooks for development

set -e

echo "Setting up pre-commit hooks..."

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
echo "Running pre-commit on all files..."
pre-commit run --all-files

echo "Pre-commit setup complete!"
```

#### 1.3 Update pyproject.toml

**Add Development Dependencies:**

```toml
[tool.poetry.group.dev.dependencies]
black = "^24.0.0"
pytest = "^8.0.0"
pre-commit = "^3.6.0"
isort = "^5.13.0"
flake8 = "^7.0.0"
mypy = "^1.8.0"
bandit = "^1.7.5"
commitizen = "^3.13.0"
pytest-cov = "^4.1.0"
pytest-xdist = "^3.5.0"
```

**Add Tool Configurations:**

```toml
[tool.isort]
profile = "black"
line_length = 120
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.flake8]
max-line-length = 120
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    "__pycache__",
    "build",
    "dist",
    ".venv",
    ".pytest_cache"
]

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.bandit]
exclude_dirs = ["tests", "build", "dist"]
skips = ["B101", "B601"]

[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"
tag_format = "v$version"
version_scheme = "pep440"
```

### Phase 2: GitHub Actions Workflows

#### 2.1 Pull Request Workflow (`.github/workflows/pr.yml`)

**New File: `.github/workflows/pr.yml`**

```yaml
name: Pull Request

on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]

jobs:
  code-quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v3
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root

      - name: Install project
        run: poetry install --no-interaction

      - name: Validate Poetry configuration
        run: |
          poetry check
          poetry debug info

      - name: Run pre-commit
        run: |
          poetry run pre-commit install
          poetry run pre-commit run --all-files

  test:
    name: Test Suite
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13']
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v3
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root

      - name: Install project
        run: poetry install --no-interaction

      - name: Run tests
        run: |
          poetry run pytest tests/ -v --cov=src/deployment_builder --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        if: matrix.os == 'ubuntu-latest'
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: false

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Run bandit security scan
        run: |
          poetry run bandit -r src/ -f json -o bandit-report.json
          poetry run bandit -r src/ -f txt

      - name: Upload bandit report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: bandit-report
          path: bandit-report.json

  build:
    name: Build Package
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Build package
        run: poetry build --verbose

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/

  test-pypi:
    name: Test PyPI Publishing
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'pull_request'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Configure test PyPI repository
        run: |
          poetry config repositories.testpypi https://test.pypi.org/legacy/

      - name: Build package
        run: poetry build --verbose

      - name: Publish to Test PyPI
        env:
          TEST_PYPI_API_TOKEN: ${{ secrets.TEST_PYPI_API_TOKEN }}
        run: |
          poetry config pypi-token.testpypi $TEST_PYPI_API_TOKEN
          poetry publish --repository testpypi

      - name: Test installation from Test PyPI
        run: |
          pip install --index-url https://test.pypi.org/simple/ deployment-builder
          deploy --version
```

#### 2.2 Main Branch Workflow (`.github/workflows/main.yml`)

**New File: `.github/workflows/main.yml`**

```yaml
name: Main Branch

on:
  push:
    branches: [main]

jobs:
  test:
    name: Test Suite
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.13']
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Load cached venv
        id: cached-poetry-dependencies
        uses: actions/cache@v3
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
        run: poetry install --no-interaction --no-root

      - name: Install project
        run: poetry install --no-interaction

      - name: Run tests
        run: |
          poetry run pytest tests/ -v --cov=src/deployment_builder --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        if: matrix.os == 'ubuntu-latest'
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: false

  integration-test:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Install kind
        run: |
          curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
          chmod +x ./kind
          sudo mv ./kind /usr/local/bin/kind

      - name: Run integration tests
        run: |
          poetry run pytest tests/test_cli_integration.py -v

  build:
    name: Build and Test Package
    runs-on: ubuntu-latest
    needs: [test, integration-test]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Build package
        run: poetry build --verbose

      - name: Test package installation
        run: |
          pip install dist/*.whl
          deploy --help

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

#### 2.3 Release Workflow (`.github/workflows/release.yml`)

**New File: `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --no-interaction

      - name: Build package
        run: poetry build --verbose

      - name: Test PyPI dry-run
        env:
          PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          poetry config pypi-token.pypi $PYPI_API_TOKEN
          poetry publish --dry-run

      - name: Publish to PyPI
        env:
          PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          poetry config pypi-token.pypi $PYPI_API_TOKEN
          poetry publish

      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
          body: |
            ## Changes in this Release
            
            See the [changelog](CHANGELOG.md) for detailed information.
            
            ## Installation
            
            ```bash
            pip install deployment-builder==${{ github.ref_name }}
            ```
            
            ## Verification
            
            ```bash
            deploy --version
            ```

  test-release:
    name: Test Release
    runs-on: ubuntu-latest
    needs: release
    steps:
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install released package
        run: |
          pip install deployment-builder==${{ github.ref_name }}

      - name: Test installation
        run: |
          deploy --version
          deploy --help
```

#### 2.4 Dependency Update Workflow (`.github/workflows/dependencies.yml`)

**New File: `.github/workflows/dependencies.yml`**

```yaml
name: Update Dependencies

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  update-dependencies:
    name: Update Dependencies
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: latest
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Update dependencies
        run: |
          # Update all dependencies to latest compatible versions
          poetry update
          
          # Export requirements for compatibility
          poetry export -f requirements.txt --output requirements.txt --without-hashes
          
          # Show what was updated
          poetry show --outdated

      - name: Test updated dependencies
        run: |
          poetry install
          poetry run pytest tests/ -v

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'chore: update dependencies'
          title: 'chore: update dependencies'
          body: |
            This PR updates project dependencies to their latest versions.
            
            ## Changes
            - Updated all dependencies to latest compatible versions
            - Updated requirements.txt
            
            ## Testing
            - [ ] All tests pass
            - [ ] No breaking changes introduced
            
            ## Poetry Commands Used
            - `poetry update` - Updated all dependencies
            - `poetry export` - Generated requirements.txt
            - `poetry show --outdated` - Listed outdated packages
          branch: update-dependencies
          delete-branch: true
```

**Enhanced Dependency Management:**
Based on the [Poetry CLI documentation](https://python-poetry.org/docs/cli/), Poetry provides advanced dependency management capabilities:

- `poetry update` updates all dependencies to latest compatible versions
- `poetry update package1 package2` updates specific packages only
- `poetry show --outdated` shows which packages have newer versions available
- `poetry export` creates requirements.txt for compatibility with pip
- `poetry check` validates pyproject.toml configuration
- `poetry lock` updates the lock file without installing

**Poetry Configuration and Validation:**
Based on the [Poetry CLI documentation](https://python-poetry.org/docs/cli/), Poetry provides comprehensive configuration and validation:

- `poetry check` validates pyproject.toml syntax and dependencies
- `poetry config` manages Poetry configuration (repositories, tokens, etc.)
- `poetry debug info` shows detailed environment information
- `poetry debug resolve` shows dependency resolution details
- `poetry list` shows installed packages
- `poetry show` shows package information and dependencies

**Enhanced CI/CD Validation:**
```bash
# Validate project configuration
poetry check

# Show dependency resolution details
poetry debug resolve

# Show environment information
poetry debug info

# List installed packages
poetry list

# Show specific package information
poetry show package-name
```

### Phase 3: PyPI Distribution Setup

#### 3.1 Poetry Build and Publish Commands

Based on the [Poetry CLI documentation](https://python-poetry.org/docs/cli/), the `build` and `publish` commands have specific options and behaviors that should be leveraged in our CI/CD pipeline:

**Poetry Build Command:**
- `poetry build` builds both wheel and source distribution (sdist) by default
- Creates packages in the `dist/` directory
- Supports `--format` option to build specific formats (wheel, sdist, or both)
- Automatically handles PEP 440-compliant versioning
- Validates package metadata before building

**Poetry Publish Command:**
- `poetry publish` publishes to PyPI by default
- Supports `--repository` option for custom repositories (e.g., test PyPI)
- Requires authentication via `poetry config pypi-token.pypi <token>`
- Supports `--dry-run` for testing without actual publishing
- Automatically uploads both wheel and source distribution

**Enhanced Build Process:**
```bash
# Build with specific format validation
poetry build --format wheel

# Build with verbose output for debugging
poetry build --verbose

# Dry run publish for testing
poetry publish --dry-run

# Publish to test PyPI
poetry publish --repository testpypi
```

**Poetry Version Management:**
Based on the [Poetry version command documentation](https://python-poetry.org/docs/cli/#version), Poetry provides powerful version management capabilities:

- `poetry version` shows current version or bumps version automatically
- Supports semantic versioning with rules: `patch`, `minor`, `major`, `prepatch`, `preminor`, `premajor`, `prerelease`
- `poetry version --short` outputs version number only
- `poetry version --dry-run` shows what would be changed without updating files
- Automatic PEP 440-compliant version validation

**Enhanced Release Script:**
```bash
#!/bin/bash
# Enhanced release script using Poetry version management

set -e

# Get current version
CURRENT_VERSION=$(poetry version --short)
echo "Current version: $CURRENT_VERSION"

# Show available version rules
echo "Available version rules: patch, minor, major, prepatch, preminor, premajor, prerelease"
read -p "Enter version rule or new version: " VERSION_INPUT

# Update version using Poetry
if [[ "$VERSION_INPUT" =~ ^(patch|minor|major|prepatch|preminor|premajor|prerelease)$ ]]; then
    poetry version "$VERSION_INPUT"
else
    poetry version "$VERSION_INPUT"
fi

# Get new version
NEW_VERSION=$(poetry version --short)
echo "New version: $NEW_VERSION"

# Continue with release process...
```

#### 3.2 PyPI Configuration

**Update `pyproject.toml` for PyPI:**

```toml
[project]
name = "deployment-builder"
version = "0.1.0"
description = "A CLI tool for creating and managing Kubernetes clusters with Kind"
authors = [
    {name = "Jim Fitzpatrick", email = "jimfity@gmail.com"}
]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.13"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities",
]
keywords = ["kubernetes", "kind", "deployment", "cli", "devops"]
dependencies = [
    "click>=8.0.0",
    "pyyaml>=6.0",
    "tomli>=2.0.0",
]

[project.urls]
Homepage = "https://github.com/Boomatang/deployment-builder"
Repository = "https://github.com/Boomatang/deployment-builder"
Documentation = "https://github.com/Boomatang/deployment-builder#readme"
"Bug Tracker" = "https://github.com/Boomatang/deployment-builder/issues"

[project.scripts]
deploy = "deployment_builder.cli:cli"

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

#### 3.2 PyPI Secrets Setup

**GitHub Secrets Required:**
- `PYPI_API_TOKEN`: PyPI API token for publishing
- `GITHUB_TOKEN`: GitHub token for repository access

**Setup Instructions:**
1. Create PyPI account and generate API token
2. Add `PYPI_API_TOKEN` to GitHub repository secrets
3. `GITHUB_TOKEN` is automatically provided by GitHub Actions

### Phase 4: Documentation and Release Management

#### 4.1 Changelog Management

**New File: `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release

## [0.1.0] - 2024-01-XX

### Added
- Basic cluster creation functionality
- Configuration management
- CLI interface
- Kind integration
```

#### 4.2 Release Management Script

**New File: `scripts/release.sh`**

```bash
#!/bin/bash
# Enhanced release management script using Poetry version management

set -e

# Check if we're on main branch
if [ "$(git branch --show-current)" != "main" ]; then
    echo "Error: Must be on main branch to create release"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean"
    exit 1
fi

# Get current version using Poetry
CURRENT_VERSION=$(poetry version --short)
echo "Current version: $CURRENT_VERSION"

# Show available version rules
echo "Available version rules: patch, minor, major, prepatch, preminor, premajor, prerelease"
echo "Or enter a specific version (e.g., 1.2.3)"
read -p "Enter version rule or new version: " VERSION_INPUT

# Validate version input
if [[ "$VERSION_INPUT" =~ ^(patch|minor|major|prepatch|preminor|premajor|prerelease)$ ]]; then
    echo "Using Poetry version rule: $VERSION_INPUT"
    poetry version "$VERSION_INPUT"
elif [[ "$VERSION_INPUT" =~ ^[0-9]+\.[0-9]+\.[0-9]+.*$ ]]; then
    echo "Using specific version: $VERSION_INPUT"
    poetry version "$VERSION_INPUT"
else
    echo "Error: Invalid version input. Use a version rule or specific version."
    exit 1
fi

# Get new version
NEW_VERSION=$(poetry version --short)
echo "New version: $NEW_VERSION"

# Dry run to show what would be published
echo "Running dry-run publish to validate package..."
poetry publish --dry-run

# Update changelog
echo "Please update CHANGELOG.md with the new version information"
read -p "Press Enter when changelog is updated..."

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to $NEW_VERSION"

# Create tag
git tag "v$NEW_VERSION"

# Push changes
git push origin main
git push origin "v$NEW_VERSION"

echo "Release $NEW_VERSION created and pushed!"
echo "GitHub Actions will automatically publish to PyPI."
```

#### 4.3 GitHub Release Template

**New File: `.github/RELEASE_TEMPLATE.md`**

```markdown
## Changes in this Release

### Added
- List new features

### Changed
- List changes to existing functionality

### Fixed
- List bug fixes

### Removed
- List removed features

## Installation

```bash
pip install deployment-builder==VERSION
```

## Verification

```bash
deploy --version
deploy --help
```

## Breaking Changes

If any breaking changes, list them here with migration instructions.

## Migration Guide

If migration is needed, provide step-by-step instructions.
```

### Phase 5: Testing Enhancements

#### 5.1 Test Configuration Updates

**Update `pyproject.toml` test configuration:**

```toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src/deployment_builder",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-fail-under=80"
]
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "fast: Fast running tests",
    "cli: CLI command tests",
    "config: Configuration tests",
    "kind: Kind integration tests",
    "kubeconfig: Kubeconfig tests"
]
```

#### 5.2 Test Coverage Configuration

**New File: `.coveragerc`**

```ini
[run]
source = src/deployment_builder
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/migrations/*"
]

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

#### 5.3 Performance Testing

**New File: `tests/test_performance.py`**

```python
import pytest
import time
from deployment_builder.cli import cli
from click.testing import CliRunner

class TestPerformance:
    def test_cli_startup_time(self):
        """Test CLI startup time is reasonable."""
        start_time = time.time()
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        end_time = time.time()
        
        assert result.exit_code == 0
        assert (end_time - start_time) < 2.0  # Should start in under 2 seconds
    
    @pytest.mark.slow
    def test_large_config_processing(self):
        """Test processing of large configuration files."""
        # Test with large configuration files
        pass
```

### Phase 6: Security and Compliance

#### 6.1 Security Scanning

**New File: `scripts/security-scan.sh`**

```bash
#!/bin/bash
# Security scanning script

set -e

echo "Running security scans..."

# Bandit security scan
echo "Running bandit..."
poetry run bandit -r src/ -f json -o bandit-report.json
poetry run bandit -r src/ -f txt

# Safety check for known vulnerabilities
echo "Running safety check..."
poetry run safety check

# Check for secrets
echo "Checking for secrets..."
poetry run detect-secrets scan --all-files

echo "Security scans complete!"
```

#### 6.2 Dependency Security

**Update `pyproject.toml` with security tools:**

```toml
[tool.poetry.group.dev.dependencies]
# ... existing dependencies ...
safety = "^2.3.5"
detect-secrets = "^1.4.0"
```

#### 6.3 License and Legal

**New File: `LICENSE`**

```text
MIT License

Copyright (c) 2024 Jim Fitzpatrick

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Phase 7: Monitoring and Metrics

#### 7.1 Code Quality Metrics

**New File: `scripts/quality-metrics.sh`**

```bash
#!/bin/bash
# Code quality metrics script

set -e

echo "Generating code quality metrics..."

# Code coverage
echo "Generating coverage report..."
poetry run pytest --cov=src/deployment_builder --cov-report=html --cov-report=xml

# Complexity analysis
echo "Running complexity analysis..."
poetry run radon cc src/deployment_builder -a

# Maintainability index
echo "Running maintainability analysis..."
poetry run radon mi src/deployment_builder

# Documentation coverage
echo "Checking documentation coverage..."
poetry run interrogate src/deployment_builder

echo "Quality metrics complete!"
```

#### 7.2 Performance Monitoring

**New File: `scripts/performance-benchmark.sh`**

```bash
#!/bin/bash
# Performance benchmarking script

set -e

echo "Running performance benchmarks..."

# CLI startup time
echo "Testing CLI startup time..."
time poetry run deploy --help

# Configuration loading time
echo "Testing configuration loading..."
time poetry run deploy create --config examples/config.toml --dry-run

# Memory usage
echo "Testing memory usage..."
poetry run python -m memory_profiler src/deployment_builder/cli.py --help

echo "Performance benchmarks complete!"
```

## Implementation Timeline

### Week 1: Pre-commit and Local Development
- [ ] Set up pre-commit configuration
- [ ] Install pre-commit hooks
- [ ] Update pyproject.toml with development dependencies
- [ ] Test local development workflow

### Week 2: GitHub Actions Setup
- [ ] Create pull request workflow
- [ ] Create main branch workflow
- [ ] Set up test matrix across Python versions and OS
- [ ] Configure caching and optimization

### Week 3: PyPI Distribution
- [ ] Set up PyPI configuration
- [ ] Create release workflow
- [ ] Test PyPI publishing
- [ ] Set up GitHub secrets

### Week 4: Testing and Quality
- [ ] Enhance test configuration
- [ ] Add performance tests
- [ ] Set up code coverage reporting
- [ ] Configure security scanning

### Week 5: Documentation and Release Management
- [ ] Create changelog management
- [ ] Set up release scripts
- [ ] Create GitHub release templates
- [ ] Document CI/CD processes

### Week 6: Monitoring and Optimization
- [ ] Set up quality metrics
- [ ] Configure performance monitoring
- [ ] Optimize CI/CD performance
- [ ] Final testing and validation

## Risk Assessment

### High Risk
- **PyPI Publishing**: Risk of publishing broken packages
- **Security**: Exposed secrets or vulnerabilities
- **Performance**: CI/CD pipeline too slow or resource-intensive

### Medium Risk
- **Dependency Updates**: Automated updates may introduce breaking changes
- **Test Coverage**: Insufficient test coverage may miss issues
- **Documentation**: Outdated or incorrect documentation

### Low Risk
- **Pre-commit Hooks**: May slow down local development
- **GitHub Actions**: May hit rate limits or quotas

## Mitigation Strategies

### PyPI Publishing
- Test PyPI publishing for PR validation
- Comprehensive testing before release
- Rollback procedures for broken releases

### Security
- Regular security scanning
- Secret rotation and management
- Dependency vulnerability monitoring

### Performance
- Optimize CI/CD workflows
- Use caching effectively
- Monitor resource usage

## Success Criteria

### Functional Requirements
- [ ] Pre-commit hooks working locally
- [ ] GitHub Actions workflows passing
- [ ] PyPI publishing automated
- [ ] Release management streamlined

### Quality Requirements
- [ ] Code coverage > 80%
- [ ] All security scans passing
- [ ] Performance benchmarks met
- [ ] Documentation up to date

### Operational Requirements
- [ ] CI/CD pipeline runs in < 10 minutes
- [ ] Automated dependency updates working
- [ ] Release process fully automated
- [ ] Monitoring and alerting configured

## Future Enhancements

### Advanced CI/CD Features
- **Multi-environment Testing**: Test against multiple Kubernetes versions
- **Performance Regression Testing**: Automated performance benchmarks
- **Security Scanning**: Advanced security analysis
- **Compliance Checking**: Automated compliance validation

### Distribution Enhancements
- **Docker Images**: Containerized distribution
- **Homebrew Formula**: macOS package management
- **Snap Package**: Linux snap distribution
- **Chocolatey Package**: Windows package management

### Monitoring and Analytics
- **Usage Analytics**: Track package usage
- **Error Reporting**: Automated error collection
- **Performance Metrics**: Real-time performance monitoring
- **User Feedback**: Automated feedback collection

## Poetry Integration Summary

This CI/CD plan leverages the full power of Poetry's CLI capabilities as documented in the [Poetry CLI documentation](https://python-poetry.org/docs/cli/):

### Key Poetry Commands Used:
- **`poetry build --verbose`**: Enhanced package building with detailed output
- **`poetry publish --dry-run`**: Safe testing before actual publishing
- **`poetry publish --repository testpypi`**: Test PyPI publishing for PR validation
- **`poetry version`**: Automated semantic versioning with rules (patch, minor, major, etc.)
- **`poetry check`**: Configuration validation and dependency checking
- **`poetry debug resolve`**: Dependency resolution validation
- **`poetry update`**: Automated dependency updates
- **`poetry export`**: Requirements.txt generation for compatibility
- **`poetry show --outdated`**: Dependency status monitoring

### Enhanced Workflows:
1. **Pull Request Workflow**: Includes Poetry validation and test PyPI publishing
2. **Main Branch Workflow**: Comprehensive testing with Poetry configuration validation
3. **Release Workflow**: Dry-run validation before PyPI publishing
4. **Dependency Update Workflow**: Automated updates with Poetry's dependency management

### Benefits of Poetry Integration:
- **PEP 440 Compliance**: Automatic version validation and formatting
- **Dependency Resolution**: Advanced dependency management and conflict resolution
- **Repository Management**: Support for multiple PyPI repositories (main and test)
- **Configuration Validation**: Built-in pyproject.toml validation
- **Lock File Management**: Deterministic dependency resolution
- **Export Capabilities**: Compatibility with pip and other tools

## Conclusion

This comprehensive CI/CD plan provides a robust foundation for the deployment-builder project, ensuring code quality, automated testing, and streamlined distribution. The implementation follows industry best practices and integrates well with the existing project structure and future enhancement plans.

The key benefits of this implementation:
1. **Quality Assurance**: Automated code quality enforcement
2. **Reliability**: Comprehensive testing and validation
3. **Efficiency**: Streamlined development and release processes
4. **Security**: Automated security scanning and compliance
5. **Maintainability**: Automated dependency updates and monitoring
6. **Poetry Integration**: Full leverage of Poetry's advanced CLI capabilities

This CI/CD pipeline will support the project's growth and ensure high-quality releases while maintaining development velocity and code quality standards.
