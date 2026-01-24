# Agent Issue Handler Workflow

This document describes the GitHub Actions workflow that automatically processes issues and creates pull requests to resolve them.

## 🎯 Overview

The Agent Issue Handler workflow enables automated processing of GitHub issues. When an issue is labeled with `agent-task` or `automation`, the workflow:

1. **Analyzes** the issue requirements
2. **Creates** a dedicated branch
3. **Implements** automated changes
4. **Validates** changes with linting and tests
5. **Creates** a pull request for review

## 🚀 How to Use

### Triggering the Workflow

1. **Create an issue** in the repository (or use an existing one)
2. **Add a trigger label** to the issue:
   - `agent-task` - For general automated tasks
   - `automation` - For automation-related tasks

The workflow will automatically start processing the issue.

### Example: Using GitHub CLI

```bash
# Create a new issue with agent-task label
gh issue create \
  --title "Add feature: User authentication" \
  --body "Please implement basic user authentication with username and password" \
  --label "agent-task"

# Add label to existing issue
gh issue edit 123 --add-label "agent-task"
```

### Example: Using GitHub Web UI

1. Go to the Issues tab in your repository
2. Click "New Issue" or open an existing issue
3. In the right sidebar, under "Labels", add `agent-task` or `automation`
4. The workflow will trigger automatically

## 📋 Workflow Process

### Stage 1: Label Check
- Validates that the issue has the required label (`agent-task` or `automation`)
- Extracts issue details (title, body, number)

### Stage 2: Notification
- Posts a comment on the issue indicating the workflow has started
- Includes a link to the workflow run for tracking

### Stage 3: Processing
1. **Checkout Repository**: Gets the latest code
2. **Create Branch**: Creates a branch named `agent/issue-<number>`
3. **Analyze Issue**: Parses the issue content and generates a plan
4. **Execute Changes**: Makes automated code changes (placeholder for AI integration)
5. **Run Linting**: Validates code style with `ruff`
6. **Run Type Checking**: Validates types with `mypy`
7. **Run Tests**: Executes test suite with `pytest`
8. **Commit Changes**: Creates a commit with detailed message
9. **Push Branch**: Pushes the branch to remote
10. **Create PR**: Opens a pull request linking to the original issue

### Stage 4: Completion
- Posts a final comment on the issue with:
  - Success status and PR link (if successful)
  - Error message and logs link (if failed)
  - Cancellation notice (if cancelled)

## 🔒 Security Features

The workflow implements enterprise-grade security practices:

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

### Integrate with AI Services

Replace the placeholder in the "Execute automated changes" step:

```yaml
- name: Execute automated changes
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    python scripts/ai_agent.py \
      --issue-number "${{ github.event.issue.number }}" \
      --issue-title "${{ needs.check-label.outputs.issue-title }}" \
      --issue-body "${{ needs.check-label.outputs.issue-body }}"
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

The workflow uses `GITHUB_TOKEN` which is automatically provided. For additional integrations, add secrets:

```bash
# Add secrets using GitHub CLI
gh secret set AI_SERVICE_TOKEN --body "your-token-here"
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/..."

# Or use the GitHub Web UI
# Settings → Secrets and variables → Actions → New repository secret
```

## 📋 Workflow YAML Schema

For reference, the workflow follows this structure:

```yaml
name: Agent Issue Handler
on:
  issues:
    types: [opened, labeled]

permissions:
  contents: read

jobs:
  check-label:      # Validates labels and extracts data
  notify-start:     # Posts start comment
  process-issue:    # Main processing logic
  notify-completion: # Posts completion comment
```

## 🎓 Best Practices

1. **Start Small**: Test with simple issues first
2. **Monitor Closely**: Watch the first few runs carefully
3. **Review PRs**: Always review automated PRs before merging
4. **Iterate**: Gradually improve the agent logic based on results
5. **Document**: Keep issue descriptions clear and detailed
6. **Label Wisely**: Only use agent labels for appropriate issues
7. **Set Expectations**: Understand the workflow is a starting point, not a complete solution

## 🤝 Contributing

To improve the agent workflow:

1. Fork the repository
2. Modify `.github/workflows/agent-issue-handler.yml`
3. Test your changes thoroughly
4. Submit a pull request with:
   - Description of changes
   - Example issues to test with
   - Security considerations

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub CLI Manual](https://cli.github.com/manual/)

## 📄 License

This workflow is part of the ayaiay-cli project and is licensed under the GNU General Public License v3.0.

## 🆘 Support

If you encounter issues:

1. Check this documentation
2. Review workflow logs in the Actions tab
3. Open an issue in the repository
4. Contact the maintainers

---

**Note**: This workflow provides a foundation for automated issue handling. The "Execute automated changes" step is a placeholder that should be replaced with your actual AI/agent implementation.
