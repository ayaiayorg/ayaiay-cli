# AI-Powered Agent Issue Handler Workflow

This document describes the GitHub Actions workflow that automatically processes issues using AI to generate real code implementations and create pull requests.

## 🎯 Overview

The AI-Powered Agent Issue Handler is an intelligent automation system that can read GitHub issues and generate actual code implementations. When an issue is labeled with `agent-task` or `automation`, the workflow:

1. **Analyzes** the issue requirements and codebase context
2. **Creates** a dedicated feature branch
3. **Generates** actual code using AI (multiple strategies available)
4. **Validates** changes with linting, type checking, and tests
5. **Creates** a pull request with the implementation for review

### What Makes This Different

Unlike simple automation that just creates documentation, this workflow uses AI to:
- **Write real code** based on issue requirements
- **Understand project context** by analyzing existing code
- **Make intelligent decisions** about implementation approach
- **Generate production-ready code** following project standards

## 🤖 AI Strategies

The workflow attempts multiple strategies in order of sophistication:

### 1. Aider AI Pair Programming (Preferred)
[Aider](https://aider.chat/) is an AI pair programming tool that understands your codebase and makes intelligent edits.

**Advantages:**
- Understands full codebase context
- Makes precise edits to existing files
- Follows project conventions automatically
- Can handle complex refactoring

**Requirements:**
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` secret configured
- Supports Claude 3.5 Sonnet (recommended) or GPT-4 Turbo

### 2. Direct AI API (Alternative)
Uses Claude or GPT APIs directly to generate code from scratch.

**Advantages:**
- More control over prompts
- Generates complete new files
- Good for new features

**Requirements:**
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` secret configured

### 3. Rule-Based Plan Generation (Fallback)
Creates structured implementation plans when no AI APIs are available.

**Advantages:**
- No API keys required
- Works offline
- Provides detailed checklist

**Output:**
- Implementation plan markdown
- Task checklist
- Manual coding guidance

## 🚀 Quick Start

### Prerequisites

**Required:**
- Repository with Python project
- GitHub Actions enabled
- Write permissions for Actions

**Optional (for AI code generation):**
- Anthropic Claude API key (recommended)
- OpenAI GPT API key (alternative)

### Setup AI API Keys

To enable AI code generation, add API keys to your repository secrets:

```bash
# Using GitHub CLI
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."
# or
gh secret set OPENAI_API_KEY --body "sk-..."

# Or via GitHub Web UI:
# Settings → Secrets and variables → Actions → New repository secret
```

**Getting API Keys:**
- **Anthropic Claude**: https://console.anthropic.com/
- **OpenAI GPT**: https://platform.openai.com/api-keys

### Triggering the Workflow

**Method 1: GitHub Web UI**
1. Go to Issues tab
2. Create or open an issue with detailed requirements
3. Add label `agent-task` or `automation`
4. Workflow automatically starts

**Method 2: GitHub CLI**
```bash
# Create issue with agent-task label
gh issue create \
  --title "Add user profile feature" \
  --body "Implement user profile with name, email, and avatar" \
  --label "agent-task"

# Add label to existing issue
gh issue edit 42 --add-label "agent-task"
```

**Method 3: Via API**
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/issues/42/labels \
  -d '{"labels":["agent-task"]}'
```

## 📋 How It Works

### Stage 1: Label Check (5-10 seconds)
- Validates issue has required label
- Extracts issue title, body, and metadata
- Sanitizes input for security

### Stage 2: Start Notification (5 seconds)
- Posts comment on issue
- Indicates AI processing has started
- Provides workflow run link

### Stage 3: Code Generation (2-5 minutes)
1. **Checkout Repository**: Clones latest code
2. **Setup Python**: Installs Python 3.11 and dependencies
3. **Install AI Tools**: Installs anthropic, openai, aider-chat
4. **Create Branch**: Creates `agent/issue-<number>` branch
5. **Analyze Context**: Scans codebase structure
6. **Generate Code**: Attempts AI strategies:
   - Try Aider for intelligent edits
   - Try direct API for code generation
   - Fall back to structured plans
7. **Run Linting**: Validates code style with `ruff`
8. **Run Type Checking**: Validates types with `mypy`
9. **Run Tests**: Executes full test suite with `pytest`
10. **Commit Changes**: Creates descriptive commit
11. **Push Branch**: Pushes to remote
12. **Create PR**: Opens pull request with details

### Stage 4: Completion Notification (5 seconds)
- Posts final comment with PR link
- Indicates success, failure, or cancellation
- Provides next steps for review

## 📝 Writing Effective Issues for AI

To get the best results from the AI agent:

### ✅ Good Issue Format

```markdown
**Title:** Add email validation to user registration

**Description:**
I need email validation added to the user registration process.

**Requirements:**
- Validate email format using regex
- Check for disposable email domains
- Return clear error messages
- Add unit tests

**Acceptance Criteria:**
- Email format validation works
- Disposable emails are rejected
- Tests achieve >90% coverage
- Documentation is updated

**Context:**
The registration code is in `src/ayaiay/auth.py`.
```

### ❌ Poor Issue Format

```markdown
fix the email thing
```

**Tips for Better Results:**
- **Be Specific**: Include detailed requirements
- **Provide Context**: Mention relevant files or components
- **List Acceptance Criteria**: Define what "done" means
- **Include Examples**: Show input/output examples
- **Mention Constraints**: Note any limitations or dependencies

## 🔒 Security Features

This workflow implements enterprise-grade security:

### Action Pinning
All GitHub Actions are pinned to specific SHA commits to prevent supply-chain attacks:
- `actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11` (v4.1.1)
- `actions/setup-python@0a5c61591373683505ea898e09a3ea4f39ef2b9c` (v5.0.0)
- `actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea` (v7.0.1)

### Least Privilege Permissions
Each job has minimal permissions:
- Default: `contents: read` only
- Job-specific overrides only when necessary
- Never uses admin permissions

### Concurrency Control
```yaml
concurrency:
  group: agent-issue-${{ github.event.issue.number }}
  cancel-in-progress: false
```
Prevents multiple simultaneous runs on the same issue.

### Input Sanitization
- Issue content is sanitized using `jq`
- Multiline content handled safely with heredoc syntax
- No direct shell interpolation of user input

## 🔧 Customization

### Change Trigger Labels

Edit `.github/workflows/agent-issue-handler.yml` at line ~60:

```bash
if echo "$LABELS" | grep -q "agent-task\|automation\|custom-label"; then
```

### Modify Base Branch

Edit the PR creation step at line ~372:

```javascript
base: 'develop',  // Change from 'main' to your base branch
```

### Add Custom Validation Steps

Add additional steps in the `process-issue` job:

```yaml
- name: Run security scan
  run: |
    pip install bandit
    bandit -r src/
```

### AI Integration (Built-in!)

The workflow now includes full AI integration out of the box! No additional configuration needed beyond API keys.

**Aider AI Pair Programming (Automatic):**
```bash
# The workflow automatically uses Aider with your API key
aider --yes --auto-commits False \
  --model claude-3-5-sonnet-20241022 \
  --message "Implement: <issue requirements>"
```

**Direct API Integration (Automatic Fallback):**
```python
# Uses Anthropic or OpenAI APIs directly if Aider fails
import anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
# Generates and applies code changes
```

**Configuration:**
Just set repository secrets:
- `ANTHROPIC_API_KEY`: For Claude 3.5 Sonnet (recommended)
- `OPENAI_API_KEY`: For GPT-4 Turbo (alternative)

**No API Keys?**
The workflow still works! It generates:
- Detailed implementation plans
- Task checklists
- Architecture guidelines
- Manual coding instructions

### Add Custom AI Models

Modify the agent script to use different models:

```yaml
- name: Execute automated changes
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    # Add custom model configuration
    AIDER_MODEL: "claude-3-opus-20240229"  # Use Opus instead
  run: |
    # Workflow script automatically picks up environment variables
```

## 📊 Monitoring

### View Workflow Runs

Using GitHub CLI:
```bash
# List recent workflow runs
gh run list --workflow=agent-issue-handler.yml

# View specific run logs
gh run view <run-id> --log

# Watch a running workflow
gh run watch <run-id>
```

Using GitHub Web UI:
1. Go to the "Actions" tab
2. Select "Agent Issue Handler" from the workflows list
3. Click on a specific run to view details

### Check Issue Comments

The workflow automatically posts comments on the issue:
- **Start**: When processing begins
- **Success**: With PR link when complete
- **Failure**: With error details and logs link
- **Cancelled**: If the workflow was manually stopped

## 🐛 Troubleshooting

### Workflow Doesn't Trigger

**Problem**: Workflow doesn't start when you add the label.

**Solutions**:
- Verify the workflow file exists at `.github/workflows/agent-issue-handler.yml`
- Check that workflows are enabled in repository settings
- Ensure the label name matches exactly (`agent-task` or `automation`)
- Verify the workflow file has no YAML syntax errors

### Permission Denied Errors

**Problem**: Workflow fails with permission errors.

**Solutions**:
- Go to Settings → Actions → General → Workflow permissions
- Select "Read and write permissions"
- Check "Allow GitHub Actions to create and approve pull requests"
- Save changes and re-run the workflow

### PR Creation Fails

**Problem**: Workflow completes but no PR is created.

**Solutions**:
- Check if a PR already exists for the branch
- Verify base branch (`main`) exists
- Review branch protection rules (allow bot commits)
- Check workflow logs for specific error messages

### Test Failures

**Problem**: Tests fail during workflow execution.

**Solutions**:
- Tests run with `continue-on-error: true` by design
- Check the test logs in the workflow run details
- Review the PR description for validation results
- Tests failing won't block PR creation (intentional)

### Concurrency Issues

**Problem**: Multiple workflow runs interfere with each other.

**Solutions**:
- The workflow has built-in concurrency control
- Only one run per issue number is allowed at a time
- Wait for the current run to complete before retriggering
- Cancel stuck runs manually if needed

## 🔄 Re-running the Workflow

### Manual Re-run

If a workflow fails and you want to try again:

```bash
# Re-run entire workflow
gh run rerun <run-id>

# Re-run only failed jobs
gh run rerun <run-id> --failed
```

Or use the GitHub Web UI:
1. Go to Actions → Agent Issue Handler
2. Select the failed run
3. Click "Re-run all jobs" or "Re-run failed jobs"

### Automatic Re-trigger

To retrigger automatically:
1. Remove and re-add the `agent-task` label
2. Or edit the issue (this won't trigger by default, but you can modify the workflow)

## 📈 Advanced Usage

### Integration with GitHub Copilot

You can extend the workflow to use GitHub Copilot:

```yaml
- name: Generate code with Copilot
  uses: github/copilot-workspace@v1
  with:
    issue-number: ${{ github.event.issue.number }}
```

### Integration with External AI Services

Add a step to call your AI service:

```yaml
- name: Call AI agent API
  run: |
    curl -X POST https://your-ai-service.com/api/process \
      -H "Authorization: Bearer ${{ secrets.AI_SERVICE_TOKEN }}" \
      -H "Content-Type: application/json" \
      -d @- <<EOF
    {
      "issue_number": "${{ github.event.issue.number }}",
      "issue_title": "${{ needs.check-label.outputs.issue-title }}",
      "issue_body": "${{ needs.check-label.outputs.issue-body }}",
      "repository": "${{ github.repository }}"
    }
    EOF
```

### Slack Notifications

Add Slack notifications to track workflow progress:

```yaml
- name: Notify on Slack
  uses: slackapi/slack-github-action@v1.24.0
  with:
    payload: |
      {
        "text": "🤖 Agent processed issue #${{ github.event.issue.number }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Issue:* <${{ github.event.issue.html_url }}|#${{ github.event.issue.number }}>\n*Status:* ${{ job.status }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Email Notifications

Configure email notifications for workflow results:

```yaml
- name: Send email notification
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "Agent Workflow: Issue #${{ github.event.issue.number }}"
    body: |
      The agent has processed issue #${{ github.event.issue.number }}.

      Status: ${{ job.status }}
      Workflow Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
    to: your-email@example.com
```

## 📝 Labels Reference

The workflow recognizes these labels:

| Label | Description | Usage |
|-------|-------------|-------|
| `agent-task` | General automated tasks | Main trigger for the workflow |
| `automation` | Automation-related tasks | Alternative trigger label |
| `automated` | Marks automated PRs | Automatically added to created PRs |
| `agent-generated` | Marks agent-generated content | Automatically added to created PRs |

### Creating Labels

Use GitHub CLI to create labels:

```bash
# Create trigger labels
gh label create "agent-task" \
  --description "Issues to be processed by automated agent" \
  --color "0E8A16"

gh label create "automation" \
  --description "Automated workflow tasks" \
  --color "1D76DB"

# Create PR labels (automatically added by workflow)
gh label create "automated" \
  --description "Automated PR" \
  --color "FBCA04"

gh label create "agent-generated" \
  --description "Generated by agent" \
  --color "D4C5F9"
```

## 🔐 Secrets Management

The workflow uses `GITHUB_TOKEN` which is automatically provided. For AI code generation, add these secrets:

```bash
# Add AI API keys using GitHub CLI
gh secret set ANTHROPIC_API_KEY --body "sk-ant-api03-..."
gh secret set OPENAI_API_KEY --body "sk-..."

# Optional: Add notification secrets
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/..."

# Or use the GitHub Web UI
# Settings → Secrets and variables → Actions → New repository secret
```

**Recommended Configuration:**
- **`ANTHROPIC_API_KEY`**: For Claude 3.5 Sonnet (best results)
- **`OPENAI_API_KEY`**: For GPT-4 Turbo (alternative)

**Security Notes:**
- API keys are never logged or exposed
- Keys are only accessible to authorized workflows
- Use separate keys for different environments
- Rotate keys regularly

## 💡 AI Code Generation Examples

### Example 1: Simple Feature Addition

**Issue:**
```markdown
Title: Add JSON export to CLI

Description:
Add a --format json option to all ayaiay commands that
currently only output human-readable text.

Requirements:
- Add --format option with choices: text, json
- Default to text for backward compatibility
- Use json.dumps for JSON output
- Add tests
```

**AI Output:**
- Modifies CLI commands to add `--format` option
- Updates command handlers with JSON serialization
- Creates comprehensive tests
- Updates documentation

### Example 2: Bug Fix

**Issue:**
```markdown
Title: Fix crash when API returns 500 error

Description:
The CLI crashes with an unhandled exception when the
API returns a 500 status code.

Requirements:
- Catch HTTP 500 errors
- Display user-friendly error message
- Log the error for debugging
- Add retry logic with exponential backoff
```

**AI Output:**
- Adds error handling in API client
- Implements retry logic with backoff
- Adds logging statements
- Creates test cases for error scenarios

### Example 3: Refactoring

**Issue:**
```markdown
Title: Extract API client into separate module

Description:
The API client code is mixed with CLI code. Extract it
into a separate, testable module.

Requirements:
- Create src/ayaiay/client.py
- Move all API logic there
- Maintain backward compatibility
- Add comprehensive tests
- Update imports
```

**AI Output:**
- Creates new client module
- Refactors existing code
- Updates all imports
- Preserves functionality
- Adds tests

## 📋 Workflow YAML Schema

For reference, the workflow follows this structure:

```yaml
name: AI-Powered Agent Issue Handler
on:
  issues:
    types: [opened, labeled]

permissions:
  contents: read  # Minimal by default

jobs:
  check-label:      # Validates labels and extracts issue data
  notify-start:     # Posts start comment on issue
  process-issue:    # Main AI code generation logic
    steps:
      - Install AI dependencies (anthropic, openai, aider)
      - Execute AI code generation (3 strategies)
      - Run linting, type checking, tests
      - Commit and push changes
      - Create pull request
  notify-completion: # Posts completion comment on issue
```

## 🎓 Best Practices

### For Issue Writers
1. **Be Specific**: Clearly describe what you want
2. **Provide Context**: Mention relevant files and components
3. **List Requirements**: Break down into specific tasks
4. **Include Examples**: Show expected input/output
5. **Define Success**: State acceptance criteria

### For Reviewers
1. **Always Review AI Code**: Don't auto-merge AI-generated PRs
2. **Check Security**: Look for vulnerabilities
3. **Verify Logic**: Ensure correctness
4. **Test Thoroughly**: Run additional manual tests
5. **Check Style**: Ensure code follows project standards

### For Maintainers
1. **Start Small**: Begin with simple issues
2. **Monitor Costs**: Track AI API usage
3. **Iterate**: Improve prompts based on results
4. **Document**: Keep examples of good issues
5. **Set Expectations**: Users should understand AI limitations

### What Works Well
- ✅ Adding new CLI commands
- ✅ Bug fixes with clear reproduction steps
- ✅ Adding tests for existing code
- ✅ Documentation updates
- ✅ Simple refactoring
- ✅ Configuration changes

### What Needs Human Review
- ⚠️ Complex architectural changes
- ⚠️ Security-sensitive code
- ⚠️ Performance optimizations
- ⚠️ Breaking changes
- ⚠️ Cross-cutting concerns
- ⚠️ Design decisions

## 🤝 Contributing

To improve the agent workflow:

1. Fork the repository
2. Modify `.github/workflows/agent-issue-handler.yml`
3. Test your changes thoroughly
4. Submit a pull request with:
   - Description of changes
   - Example issues to test with
   - Security considerations

**Ideas for Improvement:**
- Support for more AI models
- Better context extraction
- Improved prompts
- Additional validation checks
- Integration with code review tools

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Aider AI Pair Programming](https://aider.chat/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## 📄 License

This workflow is part of the ayaiay-cli project and is licensed under the GNU General Public License v3.0.

## 🆘 Support

If you encounter issues:

1. **Check Documentation**: Review this guide and workflow logs
2. **Check API Keys**: Ensure AI API keys are configured correctly
3. **Review Logs**: Check Actions tab for detailed error messages
4. **Test Locally**: Try running Aider locally to debug
5. **Open Issue**: Create an issue with workflow run link
6. **Contact Maintainers**: Reach out for complex problems

## 💰 Cost Considerations

AI-powered code generation has costs associated with API usage:

### Anthropic Claude Pricing (approximate)
- **Claude 3.5 Sonnet**: $3 per million input tokens, $15 per million output tokens
- **Typical issue**: 5,000-20,000 tokens = $0.10-0.40 per issue

### OpenAI GPT Pricing (approximate)
- **GPT-4 Turbo**: $10 per million input tokens, $30 per million output tokens
- **Typical issue**: 5,000-20,000 tokens = $0.20-0.80 per issue

### Cost Management Tips
1. Use Claude 3.5 Sonnet (more cost-effective)
2. Be selective with agent-task labels
3. Set API rate limits
4. Monitor usage in AI provider dashboard
5. Use rule-based fallback for simple issues

### Without API Keys
The workflow still provides value without AI API keys:
- Generates structured implementation plans
- Creates task checklists
- Provides coding guidelines
- Documents requirements
- **Cost: $0**

---

**Note**: This workflow now includes full AI-powered code generation! Configure `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in repository secrets to enable autonomous coding. Without API keys, it generates detailed implementation plans.
