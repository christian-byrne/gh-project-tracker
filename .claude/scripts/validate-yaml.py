#!/usr/bin/env python3
"""
Validate and fix YAML template files for the GitHub Issue Tracker.
Checks for common corruption patterns and fixes them.
"""

import yaml
import sys
import os
from pathlib import Path
import re

def check_yaml_file(filepath):
    """Check a YAML file for common issues."""
    issues = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for Python type annotations
    if '!!python/object' in content:
        issues.append("Contains Python type annotations (!!python/object)")
    
    # Check for enum representations
    enum_pattern = r'<\w+\.\w+:\s*[\'"]?\w+[\'"]?>'
    if re.search(enum_pattern, content):
        issues.append("Contains enum object representations")
    
    # Try to parse the YAML
    try:
        data = yaml.safe_load(content)
        
        # Check for required fields
        if not isinstance(data, dict):
            issues.append("Root element is not a dictionary")
        else:
            if 'repos' not in data:
                issues.append("Missing 'repos' field")
            if 'name' not in data:
                issues.append("Missing 'name' field")
                
        # Check status_overrides values are strings
        if 'status_overrides' in data:
            for key, value in data.get('status_overrides', {}).items():
                if not isinstance(value, str):
                    issues.append(f"status_override '{key}' has non-string value: {type(value)}")
                    
    except yaml.YAMLError as e:
        issues.append(f"YAML parsing error: {e}")
    
    return issues

def fix_yaml_file(filepath):
    """Attempt to fix common YAML issues."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Remove Python type annotations
    content = re.sub(r'!!python/object[^\n]*\n\s*-\s*', '', content)
    
    # Fix enum representations
    # Convert <IssueStatus.TODO: 'todo'> to 'todo'
    content = re.sub(r'<\w+\.(\w+):\s*[\'"]?(\w+)[\'"]?>', r"'\2'", content)
    
    # Save backup if content changed
    if content != original_content:
        backup_path = f"{filepath}.bak"
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"Created backup: {backup_path}")
        
        # Write fixed content
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    
    return False

def main():
    """Validate all YAML files in templates directory."""
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        print("No templates directory found")
        return 1
    
    yaml_files = list(templates_dir.glob("*.yaml")) + list(templates_dir.glob("*.yml"))
    
    if not yaml_files:
        print("No YAML files found in templates directory")
        return 0
    
    all_valid = True
    
    for filepath in yaml_files:
        print(f"\nChecking {filepath}...")
        issues = check_yaml_file(filepath)
        
        if issues:
            all_valid = False
            print(f"❌ Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            
            # Attempt to fix
            if '--fix' in sys.argv:
                if fix_yaml_file(filepath):
                    # Re-validate after fix
                    new_issues = check_yaml_file(filepath)
                    if not new_issues:
                        print(f"✅ Successfully fixed!")
                    else:
                        print(f"⚠️  Some issues remain after fix")
        else:
            print(f"✅ Valid YAML")
    
    if not all_valid and '--fix' not in sys.argv:
        print("\nRun with --fix flag to attempt automatic fixes")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())