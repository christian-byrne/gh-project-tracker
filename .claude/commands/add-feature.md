# Add New Feature to Issue Tracker

<role>
You are a Python developer experienced with Textual TUI framework and GitHub API integration.
</role>

<task>
Add a new feature to the GitHub issue tracker: $ARGUMENTS
</task>

<instructions>
1. **Understand the Current Architecture**
   - Read tui.py to understand UI patterns
   - Review models.py for data structures
   - Check github_client.py for API integration
   - Examine existing features for patterns to follow

2. **Plan the Implementation**
   Think hard about:
   - What UI changes are needed?
   - What new data models are required?
   - What API calls need to be added?
   - How will this integrate with existing features?

3. **Update Models (if needed)**
   - Add new fields to Pydantic models
   - Ensure proper type hints
   - Add validation where necessary
   - Update model_dump methods if needed

4. **Implement UI Changes**
   - Follow Textual patterns from existing code
   - Use synchronous self.refresh() - NEVER async
   - Escape any user-provided text with \[ and \]
   - Add keyboard shortcuts if appropriate

5. **Extend API Client (if needed)**
   - Add methods to GitHubClient class
   - Use sequential processing, not parallel
   - Include proper error handling
   - Update cache keys if adding parameters

6. **Test Thoroughly**
   - Run the app and test the new feature
   - Test error cases
   - Verify YAML persistence works
   - Check cache behavior

7. **Update Documentation**
   - Add the feature to CLAUDE.md
   - Document any new pitfalls discovered
   - Update command list if new shortcuts added
</instructions>

<examples>
<example>
User Input: "add ability to assign issues to users"
Implementation would involve:
- Adding assignee field to Issue model
- Creating AssignDialog widget in tui.py
- Adding assign_issue method to GitHubClient
- Binding 'a' key to show assign dialog
- Updating issue display to show assignee
</example>
</examples>

<constraints>
- Follow existing code patterns exactly
- Don't use async where sync is expected
- Always handle errors gracefully
- Preserve all existing functionality
- Test with real GitHub data
</constraints>