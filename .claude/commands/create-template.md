# Create New Issue Tracker Template

<role>
You are an expert in YAML configuration and GitHub repository management.
</role>

<task>
Create a new template configuration file for tracking issues across multiple GitHub repositories with specific filtering conditions.
</task>

<instructions>
1. **Gather Requirements**
   - Ask which repositories to track
   - Understand what filtering conditions are needed
   - Determine if custom statuses are required
   - Check if discussions should be included

2. **Create Template Structure**
   ```yaml
   name: "Template Name"
   repos:
     - owner: "org-or-user"
       name: "repo-name"
     # Add more repos as needed
   
   conditions:
     - field: "state"
       operator: "equals"
       value: "open"
     # Add more conditions
   
   condition_logic: "AND"  # or "OR"
   
   # Optional sections:
   status_overrides:
     '123': 'in_progress'
   
   settings:
     include_discussions: false  # Set to true carefully - can timeout
   ```

3. **Validate Field Names**
   Valid condition fields:
   - state (open/closed)
   - labels (comma-separated)
   - assignee
   - milestone
   - created_at / updated_at (ISO date)
   
   Valid operators:
   - equals, not_equals
   - contains, not_contains
   - greater_than, less_than (for dates)

4. **Best Practices**
   - Start with include_discussions: false (prevents timeouts)
   - Use specific label names, not wildcards
   - Keep repo count reasonable (5-10 max for performance)
   - Test with simple conditions first

5. **Save and Test**
   - Save to templates/[meaningful-name].yaml
   - Run the app and load the template
   - Verify results match expectations
</instructions>

<examples>
<example>
Simple template tracking TODOs:
```yaml
name: "My TODOs"
repos:
  - owner: "myorg"
    name: "frontend"
  - owner: "myorg"
    name: "backend"
    
conditions:
  - field: "labels"
    operator: "contains"
    value: "todo"
  - field: "state"
    operator: "equals"
    value: "open"
    
condition_logic: "AND"

settings:
  include_discussions: false
```
</example>
</examples>