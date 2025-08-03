# Fix YAML Template Corruption

<role>
You are an expert in Python YAML serialization and debugging file corruption issues.
</role>

<task>
Fix corrupted YAML template files in the templates/ directory. The corruption typically happens when enum objects are saved instead of their string values, or when yaml.dump() adds Python type annotations.
</task>

<instructions>
1. First, examine all YAML files in the templates/ directory
2. Look for these corruption patterns:
   - `!!python/object` annotations
   - Enum objects instead of string values (e.g., `<IssueStatus.TODO: 'todo'>`)
   - Malformed YAML structure
3. For each corrupted file:
   - Create a backup with .bak extension
   - Fix the corruption by:
     - Removing Python type annotations
     - Converting enum representations to plain strings
     - Fixing YAML structure
   - Validate the fixed YAML can be loaded
4. Update the code to prevent future corruption:
   - Ensure yaml.safe_dump() is used everywhere
   - Check enum.value is stored, not enum object
   - Add validation before saving
5. Test the application still works with fixed files

## Expected Output

Report on:
- Which files were corrupted and how
- What fixes were applied
- Code changes made to prevent recurrence
- Verification that the app works correctly
</instructions>

<examples>
<example>
Corrupted YAML:
```yaml
status_overrides:
  '123': !!python/object/apply:github_issue_tracker.models.IssueStatus
  - 'in_progress'
```

Fixed YAML:
```yaml
status_overrides:
  '123': 'in_progress'
```
</example>
</examples>