# SVG2PPTX Development Tools

> Comprehensive development tools for project maintenance, analysis, and migration

## 📁 Structure

```
tools/
├── README.md              # This index
├── analysis/              # Code analysis tools
│   ├── analyze_svg_library.py
│   ├── collect_real_world_svgs.py
│   └── dependency_analyzer.py
├── development/           # Development utilities
│   └── base_utilities.py
├── maintenance/           # Regular maintenance tools
│   └── pre_commit_coverage.py
├── migration/             # One-time migration tools
│   ├── incremental_test_migration.py
│   ├── migrate_directory_structure.py
│   ├── migrate_drive_integration.py
│   ├── migrate_to_lxml.py
│   └── standardize_naming.py
├── reporting/             # Report generation tools
│   ├── accuracy_measurement.py
│   ├── accuracy_reporter.py
│   ├── coverage_dashboard.py
│   ├── coverage_trends.py
│   └── reporting_utilities.py
└── reports/               # Generated reports
    └── dependency_analysis_report.html
```

## 🔍 **Analysis Tools**

### `analysis/dependency_analyzer.py`
- **Purpose**: Analyze import dependencies across tools
- **Output**: HTML report showing dependency relationships
- **Usage**: `python tools/analysis/dependency_analyzer.py`

### `analysis/analyze_svg_library.py`
- **Purpose**: Analyze SVG library usage patterns
- **Function**: Identifies optimization opportunities

### `analysis/collect_real_world_svgs.py`
- **Purpose**: Collect SVG samples for testing
- **Function**: Builds comprehensive test corpus

## 🛠️ **Development Utilities**

### `development/base_utilities.py`
- **Purpose**: Common utilities for other tools
- **Contains**: DatabaseManager, HTMLReportGenerator, FileUtilities
- **Usage**: Imported by other tools for shared functionality

## 🔧 **Maintenance Tools**

### `maintenance/pre_commit_coverage.py`
- **Purpose**: Pre-commit hook for coverage validation
- **Usage**: Automatically run via git pre-commit hooks
- **Function**: Ensures test coverage standards before commits

## 🚀 **Migration Tools**

### `migration/migrate_to_lxml.py`
- **Purpose**: Convert xml.etree.ElementTree imports to lxml
- **Status**: ✅ Completed - migrated 56 files
- **Usage**: One-time migration tool (historical)

### `migration/migrate_directory_structure.py`
- **Purpose**: Reorganize test directory structure
- **Status**: ✅ Completed - restructured tests/
- **Usage**: One-time migration tool (historical)

### `migration/standardize_naming.py`
- **Purpose**: Standardize test file naming conventions
- **Status**: ✅ Completed - renamed test files
- **Usage**: One-time migration tool (historical)

### `migration/incremental_test_migration.py`
- **Purpose**: Migrate tests incrementally during refactoring
- **Status**: ✅ Completed - test migration complete
- **Usage**: One-time migration tool (historical)

### `migration/migrate_drive_integration.py`
- **Purpose**: Migrate Google Drive API integration
- **Status**: ✅ Completed - drive integration migrated
- **Usage**: One-time migration tool (historical)

## 📊 **Reporting Tools**

### `reporting/coverage_dashboard.py`
- **Purpose**: Generate interactive coverage dashboard
- **Output**: HTML dashboard with coverage trends
- **Usage**: `python tools/reporting/coverage_dashboard.py`

### `reporting/accuracy_measurement.py`
- **Purpose**: Measure conversion accuracy
- **Function**: Compares SVG input to PPTX output quality

### `reporting/accuracy_reporter.py`
- **Purpose**: Generate accuracy reports
- **Output**: Detailed accuracy analysis reports

### `reporting/coverage_trends.py`
- **Purpose**: Track coverage trends over time
- **Function**: Historical coverage analysis

## 📋 **Usage Guidelines**

### **Active Development Tools**
- **Analysis**: Run regularly to understand codebase health
- **Maintenance**: Automated tools for ongoing project health
- **Reporting**: Generate insights and track progress

### **Historical Migration Tools**
- **Migration**: One-time tools for specific migrations
- **Purpose**: Kept for historical reference and documentation
- **Status**: Generally completed, not run again

## 🗂️ **Organization Principles**

- **Single Tools Directory**: All development utilities consolidated
- **Purpose-Based Organization**: Tools grouped by function
- **Clear Documentation**: Each tool's purpose and status documented
- **Shared Utilities**: Common functionality in development/base_utilities.py

---

*This tools directory consolidates ALL development utilities with clear organization by purpose.*