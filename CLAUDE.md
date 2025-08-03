# GitHub Issue Tracker - Claude Code Development Guide

This repository is a sophisticated GitHub issue tracking TUI (Terminal User Interface) built with Python. This guide helps Claude Code agents work effectively with the codebase.

## 🎯 Project Overview

A terminal-based GitHub issue tracker with advanced filtering, custom status management, and real-time updates. Built with Textual for the TUI and integrates with GitHub's REST and GraphQL APIs.

## 📋 Core Commands

```bash
# Run the application
python -m github_issue_tracker

# Common operations
r              # Refresh issues (fetches from GitHub)
shift+r        # Force refresh (clears cache)
enter          # View issue details
space          # Toggle issue selection
s              # Set custom status
f              # Show filter dialog
/              # Search issues
q              # Quit
```

## 🏗️ Architecture Overview

### Key Components
- **TUI Layer** (`tui.py`): Textual-based interface, handles all user interactions
- **GitHub Client** (`github_client.py`): API integration, caching, rate limit handling
- **Models** (`models.py`): Pydantic models for type safety
- **Templates** (`templates/`): YAML configuration files for repos and conditions

### Important Patterns
- All UI updates use synchronous `self.refresh()` - NEVER use `await self.refresh()`
- YAML persistence uses `yaml.safe_dump()` to avoid Python type annotations
- Enum values must be converted to strings before YAML serialization
- Sequential API processing is more reliable than parallel `asyncio.gather()`

## 🐛 Critical Pitfalls & Solutions

### 1. Textual Framework Pitfalls
- **CRITICAL**: `self.refresh()` is synchronous not async - using `await self.refresh()` causes TypeError
- **Markup Errors**: Escape square brackets in error messages with `\[` and `\]` to prevent crashes
- **Debugging**: Simple `print()` doesn't work - use custom logger with immediate flush
- **Screen Navigation**: `push_screen_wait()` fails in async contexts - use `push_screen` with callbacks

### 2. YAML Serialization Issues
- **Type Annotations**: `yaml.dump()` saves `!!python/object` - must use `yaml.safe_dump()`
- **Enum Storage**: Store `enum.value` not the enum object itself
- **Corruption Detection**: When template YAML corrupts, only some repos process - others silently fail

### 3. GitHub API Quirks
- **ID Types**: API returns both int and string IDs - model fields need `int | str`
- **Pull Requests**: Issues API includes PRs - filter items with `"pull_request"` key
- **Rate Limiting**: Shows as progressively fewer results (80→18→2→0) not explicit errors
- **GraphQL Timeouts**: Discussions API can hang - disable `include_discussions` if not needed

### 4. Data Processing
- **Parallel Requests**: `asyncio.gather()` can silently drop results - use sequential processing
- **Cache Keys**: Must include ALL query parameters including `condition_logic` field
- **Pydantic Models**: `model_dump(use_enum_values=True)` doesn't always work - manual conversion needed
- **Search vs Filter**: TUI search uses fuzzy matching, API filtering is exact match

## 🔧 Development Workflow

### Making Changes
1. **Research First**: Read relevant files to understand patterns
   - Check `models.py` for data structures
   - Review `tui.py` for UI patterns
   - Study `github_client.py` for API integration

2. **Plan Thoroughly**: Use extended thinking before implementing
   ```
   Think hard about the best approach for [task]
   ```

3. **Test Incrementally**: Run the app after each change
   ```bash
   python -m github_issue_tracker
   ```

4. **Handle Errors Gracefully**: Always escape error messages and handle API failures

### Adding New Features
1. **Update Models**: Add fields to Pydantic models in `models.py`
2. **Enhance UI**: Modify Textual widgets in `tui.py`
3. **Extend API**: Add methods to `GitHubClient` class
4. **Update Templates**: Modify YAML structure if needed

## 📁 File Structure

```
github_issue_tracker/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point
├── tui.py              # Terminal UI (Textual app)
├── github_client.py    # GitHub API client
├── models.py           # Pydantic data models
├── logger.py           # Custom logging for Textual
├── cache_utils.py      # Disk caching utilities
└── templates/          # YAML configuration files
    └── *.yaml          # Repository and filter configs
```

## 🚀 Quick Fixes

### Force Refresh Not Working?
Check line 312 in `tui.py` - ensure it's `self.refresh()` not `await self.refresh()`

### YAML File Corrupted?
1. Check for enum objects instead of values
2. Look for Python type annotations (`!!python/object`)
3. Verify all status values are strings

### API Returning Fewer Results?
- Check rate limit: Add logging to see progressive reduction
- Try sequential processing instead of parallel
- Disable discussions if GraphQL times out

### Cache Issues?
- Cache key must include all parameters
- Check `condition_logic` field is included
- Use shift+r to force refresh

## 🧪 Testing Approach

1. **Manual Testing**: Run the TUI and test each feature
2. **API Testing**: Use `gh` CLI to verify API behavior
3. **Cache Testing**: Delete cache files and verify regeneration
4. **Error Testing**: Introduce deliberate errors to test handling

## 🔍 Debugging Tips

1. **Enable Logging**: Check `logger.py` configuration
2. **API Inspection**: Log raw API responses before processing
3. **State Tracking**: Add debug prints to enum conversions
4. **Cache Inspection**: Examine `.cache/` directory contents

## 📝 Code Style Guidelines

- Use type hints everywhere for better Claude Code understanding
- Keep functions focused and single-purpose
- Add docstrings for complex logic
- Use descriptive variable names
- Handle all error cases explicitly

## 🤝 Contributing

When making changes:
1. Preserve existing patterns
2. Test thoroughly with real GitHub data
3. Document any new pitfalls discovered
4. Update this CLAUDE.md with new learnings

## 🎓 Learning Resources

- [Textual Documentation](https://textual.textualize.io/)
- [GitHub REST API](https://docs.github.com/en/rest)
- [Pydantic Models](https://docs.pydantic.dev/)
- [Python YAML](https://pyyaml.org/wiki/PyYAMLDocumentation)