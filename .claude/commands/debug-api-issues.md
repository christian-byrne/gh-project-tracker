# Debug GitHub API Issues

<role>
You are a GitHub API expert specializing in rate limiting, authentication, and API response debugging.
</role>

<task>
Debug issues with the GitHub API integration in this issue tracker application. Common problems include rate limiting, incomplete results, and timeouts.
</task>

<instructions>
1. Add comprehensive logging to github_client.py:
   - Log all API requests with timestamps
   - Log response headers (especially rate limit headers)
   - Log response sizes and item counts
   - Track time taken for each request

2. Identify the specific issue:
   - Rate limiting: Look for X-RateLimit headers and decreasing result counts
   - Timeouts: Check if GraphQL/discussions queries hang
   - Auth issues: Verify token permissions
   - Incomplete data: Check pagination and parallel processing

3. Implement fixes based on findings:
   - For rate limiting: Add delays between requests
   - For timeouts: Disable problematic features (like discussions)
   - For parallel issues: Switch to sequential processing
   - For pagination: Ensure all pages are fetched

4. Test the fixes:
   - Run with a test template
   - Monitor logs for improvements
   - Verify all expected data is returned

5. Update error handling:
   - Add user-friendly error messages
   - Implement retry logic where appropriate
   - Add fallback behaviors
</instructions>

<constraints>
- Preserve existing functionality
- Don't break the cache system
- Keep changes minimal and focused
- Maintain backwards compatibility
</constraints>

## Quick Checks

Run these commands to verify API access:
```bash
# Check rate limit
gh api rate_limit

# Test basic issues fetch
gh api repos/OWNER/REPO/issues

# Test GraphQL
gh api graphql -f query='{ viewer { login } }'
```