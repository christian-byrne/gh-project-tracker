# Claude Code Resources

This directory contains specialized resources to help Claude Code agents work effectively with the GitHub Issue Tracker project.

## 📁 Directory Structure

```
.claude/
├── commands/          # Reusable prompt templates for common tasks
├── templates/         # Document templates (bugs, PRs, features)
├── hooks/            # Automated checks and validations
├── subagents/        # Specialized role definitions
├── scripts/          # Utility scripts for maintenance
└── config/           # JSON configuration files
```

## 🚀 Quick Start for Claude Agents

1. **Read CLAUDE.md** in the project root first - it contains critical project knowledge
2. **Use commands** via `/project:command-name` for common tasks
3. **Run hooks** to validate changes before committing
4. **Consult subagents** for specialized expertise
5. **Use scripts** for maintenance and debugging

## 📋 Available Commands

- `/project:fix-yaml-corruption` - Fix corrupted YAML template files
- `/project:debug-api-issues` - Debug GitHub API problems
- `/project:add-feature` - Add new features following patterns
- `/project:create-template` - Create new issue tracking templates
- `/project:fix-textual-error` - Fix Textual framework errors

## 🔧 Utility Scripts

- `validate-yaml.py` - Check and fix YAML templates
- `clear-cache.sh` - Clear the API response cache
- `test-github-api.py` - Test GitHub API connectivity

## 🤖 Subagent Specialists

- **yaml-specialist** - YAML serialization expert
- **textual-expert** - Textual TUI framework expert
- **github-api-specialist** - GitHub API optimization expert

## 🪝 Hooks

- **pre-commit.sh** - Validates code before commits
- **post-edit.sh** - Checks for common issues after edits

## ⚡ Key Reminders

1. **NEVER use `await self.refresh()`** - it's synchronous
2. **ALWAYS use `yaml.safe_dump()`** not `yaml.dump()`
3. **Store `enum.value`** not enum objects in YAML
4. **Escape brackets** in error messages with `\[` and `\]`
5. **Sequential > parallel** for API requests

## 🎯 Workflow Patterns

See `config/workflows.json` for detailed workflow definitions:
- Bug fixing workflow
- Feature addition workflow
- Code review workflow
- Debugging workflow

Each workflow includes steps, relevant commands, and resources.