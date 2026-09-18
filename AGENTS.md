
# GitHub CLI

Run authenticated `gh` commands with `sandbox_permissions: "require_escalated"`.

# GitHub issues

The issue-writing schema and conventions are in [specimen_github_issue.md](specimen_github_issue.md). Use the `agent-ready` label for issues that contain enough context, scope, and acceptance criteria for an agent to implement autonomously.

When asked to fix a GitHub issue, create a new Git worktree for that issue before making changes. Implement and verify the change in that worktree, then create a pull request with the implementation, verification results, and any remaining risks, and comment those in the issue.

Once a PR is merged, clean up the worktree.

