#!/usr/bin/env python3
"""Test runner script with performance optimization options."""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and measure execution time."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ SUCCESS - Duration: {duration:.2f}s")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return True, duration
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ FAILED - Duration: {duration:.2f}s")
        print(f"Error: {e.stderr}")
        return False, duration

def main():
    """Run tests with different performance configurations."""
    base_cmd = ["poetry", "run", "pytest"]
    
    # Test configurations
    configs = [
        {
            "cmd": base_cmd + ["tests/", "-v"],
            "description": "All tests (sequential)"
        },
        {
            "cmd": base_cmd + ["tests/", "-v", "-n", "auto"],
            "description": "All tests (parallel with auto workers)"
        },
        {
            "cmd": base_cmd + ["tests/", "-v", "-n", "4"],
            "description": "All tests (parallel with 4 workers)"
        },
        {
            "cmd": base_cmd + ["-m", "unit", "-v", "-n", "auto"],
            "description": "Unit tests only (parallel)"
        },
        {
            "cmd": base_cmd + ["-m", "integration", "-v", "-n", "auto"],
            "description": "Integration tests only (parallel)"
        },
        {
            "cmd": base_cmd + ["-m", "fast", "-v", "-n", "auto"],
            "description": "Fast tests only (parallel)"
        },
        {
            "cmd": base_cmd + ["-m", "slow", "-v"],
            "description": "Slow tests only (sequential)"
        }
    ]
    
    results = []
    
    for config in configs:
        success, duration = run_command(config["cmd"], config["description"])
        results.append({
            "description": config["description"],
            "success": success,
            "duration": duration
        })
    
    # Summary
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['description']:<50} {result['duration']:>8.2f}s")
    
    # Find fastest successful run
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        fastest = min(successful_results, key=lambda x: x["duration"])
        print(f"\n🏆 Fastest successful run: {fastest['description']} ({fastest['duration']:.2f}s)")
    
    return 0 if all(r["success"] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
