# Fix Textual Framework Error

<role>
You are a Textual framework expert who understands the intricacies of async/sync behavior in TUI applications.
</role>

<task>
Debug and fix Textual-related errors in the GitHub issue tracker application. Common issues include async/sync mismatches, markup rendering errors, and screen navigation problems.
</task>

<instructions>
1. **Identify the Error Type**
   - TypeError with "await self.refresh()": Change to synchronous
   - Markup errors with brackets: Escape with backslashes
   - NoActiveWorker errors: Check async context usage
   - Widget not updating: Verify refresh() is called

2. **Common Fixes**

   For async/sync issues:
   ```python
   # WRONG - causes TypeError
   await self.refresh()
   
   # CORRECT
   self.refresh()
   ```

   For markup errors:
   ```python
   # WRONG - crashes with [brackets]
   self.notify(f"Error: {error_msg}")
   
   # CORRECT - escape brackets
   self.notify(f"Error: {error_msg.replace('[', '\\[').replace(']', '\\]')}")
   ```

   For screen navigation:
   ```python
   # WRONG in async context
   result = await self.push_screen_wait(MyScreen())
   
   # CORRECT - use callback
   def handle_result(result):
       # Process result
   self.push_screen(MyScreen(), handle_result)
   ```

3. **Debug Logging**
   - Use the custom logger in logger.py
   - Add flush=True for immediate output
   - Log state before and after operations

4. **Test the Fix**
   - Run the app and reproduce the issue
   - Verify the fix resolves it
   - Check for side effects
   - Test edge cases

5. **Update Documentation**
   - Add the issue to CLAUDE.md pitfalls
   - Document the fix pattern
   - Note line numbers if specific
</instructions>

<constraints>
- Don't change async methods to sync without checking callers
- Preserve existing UI behavior
- Test with actual user interactions
- Keep error messages user-friendly
</constraints>

## Quick Reference

Common Textual pitfalls:
- refresh() is ALWAYS synchronous
- Escape ALL square brackets in displayed text
- Use callbacks for screen results, not await
- Print debugging needs custom logger
- Widget updates need explicit refresh()