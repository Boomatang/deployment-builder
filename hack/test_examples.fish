#!/usr/bin/env fish

# Test script for deployment-builder examples
# This script tests all example configuration files by creating and then removing clusters
#
# NOTE: For automated testing, consider using the integration tests instead:
#       poetry run pytest tests/test_cli_integration.py -v

set -l examples_dir "examples"
set -l config_files

# Find all configuration files in the examples directory
for file in $examples_dir/*.{toml,yaml,yml,json}
    if test -f "$file"
        set -a config_files "$file"
    end
end

if test (count $config_files) -eq 0
    echo "❌ No configuration files found in $examples_dir directory"
    exit 1
end

echo "🔍 Found " (count $config_files) " configuration files to test:"
for file in $config_files
    echo "  - $file"
end
echo ""

set -l success_count 0
set -l total_count (count $config_files)

for config_file in $config_files
    echo "🧪 Testing configuration: $config_file"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Test create command
    echo "📦 Creating clusters with: deploy --log-level=debug create --config $config_file"
    if poetry run deploy --log-level=debug create --config "$config_file"
        echo "✅ Create command successful for $config_file"
        
        # Wait a moment for clusters to be ready
        echo "⏳ Waiting 5 seconds for clusters to be ready..."
        sleep 5
        
        # Test remove command
        echo "🗑️  Removing clusters with: deploy --log-level=debug remove --config $config_file --force"
        if poetry run deploy --log-level=debug remove --config "$config_file" --force
            echo "✅ Remove command successful for $config_file"
            set success_count (math $success_count + 1)
        else
            echo "❌ Remove command failed for $config_file"
        end
    else
        echo "❌ Create command failed for $config_file"
    end
    
    echo ""
end

echo "📊 Test Results Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Successful: $success_count/$total_count"
echo "❌ Failed: " (math $total_count - $success_count) "/$total_count"

if test $success_count -eq $total_count
    echo "🎉 All tests passed!"
    exit 0
else
    echo "💥 Some tests failed!"
    exit 1
end
