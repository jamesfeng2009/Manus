"""GitHub tool for GitHub integration."""

import os
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class GitHubTool(Tool):
    """GitHub operations via GitHub API."""

    name = "github"
    description = "Manage GitHub issues, pull requests, and repositories"

    parameters = {
        "action": "Operation: create_issue, get_issue, close_issue, list_issues, create_pr, get_repo, search",
        "owner": "Repository owner",
        "repo": "Repository name",
        "issue_number": "Issue number (for get, close)",
        "title": "Issue/PR title",
        "body": "Issue/PR body",
        "labels": "List of labels",
        "state": "State: open, closed",
        "head": "Head branch (for PR)",
        "base": "Base branch (for PR)",
        "query": "Search query",
    }

    def __init__(self, token: str | None = None):
        self.token = token

        if not self.token:
            self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            self.token = "dummy_token_for_testing"

        self.base_url = "https://api.github.com"

    async def execute(
        self,
        action: str,
        owner: str | None = None,
        repo: str | None = None,
        issue_number: int | None = None,
        title: str | None = None,
        body: str | None = None,
        labels: list[str] | None = None,
        state: str | None = None,
        head: str | None = None,
        base: str | None = None,
        query: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }

            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                if action == "create_issue":
                    if not owner or not repo or not title:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner, repo, and title are required",
                        )

                    data = {"title": title, "body": body or ""}
                    if labels:
                        data["labels"] = labels

                    response = await client.post(
                        f"{self.base_url}/repos/{owner}/{repo}/issues",
                        json=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "issue_number": result.get("number"),
                            "url": result.get("html_url"),
                            "created": True,
                        },
                    )

                elif action == "get_issue":
                    if not owner or not repo or not issue_number:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner, repo, and issue_number are required",
                        )

                    response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                    )
                    response.raise_for_status()
                    result = response.json()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "number": result.get("number"),
                            "title": result.get("title"),
                            "body": result.get("body"),
                            "state": result.get("state"),
                            "labels": [l.get("name") for l in result.get("labels", [])],
                            "url": result.get("html_url"),
                        },
                    )

                elif action == "close_issue":
                    if not owner or not repo or not issue_number:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner, repo, and issue_number are required",
                        )

                    response = await client.patch(
                        f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                        json={"state": "closed"},
                    )
                    response.raise_for_status()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"issue_number": issue_number, "closed": True},
                    )

                elif action == "list_issues":
                    if not owner or not repo:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner and repo are required",
                        )

                    params = {"state": state or "open"}
                    response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/issues",
                        params=params,
                    )
                    response.raise_for_status()
                    results = response.json()

                    issues = [
                        {
                            "number": i.get("number"),
                            "title": i.get("title"),
                            "state": i.get("state"),
                            "labels": [l.get("name") for l in i.get("labels", [])],
                        }
                        for i in results
                        if "pull_request" not in i
                    ]

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"issues": issues, "count": len(issues)},
                    )

                elif action == "create_pr":
                    if not owner or not repo or not title or not head or not base:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner, repo, title, head, and base are required",
                        )

                    data = {
                        "title": title,
                        "body": body or "",
                        "head": head,
                        "base": base,
                    }

                    response = await client.post(
                        f"{self.base_url}/repos/{owner}/{repo}/pulls",
                        json=data,
                    )
                    response.raise_for_status()
                    result = response.json()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "pr_number": result.get("number"),
                            "url": result.get("html_url"),
                            "created": True,
                        },
                    )

                elif action == "get_repo":
                    if not owner or not repo:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="owner and repo are required",
                        )

                    response = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}",
                    )
                    response.raise_for_status()
                    result = response.json()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "name": result.get("name"),
                            "full_name": result.get("full_name"),
                            "description": result.get("description"),
                            "stars": result.get("stargazers_count"),
                            "forks": result.get("forks_count"),
                            "language": result.get("language"),
                            "url": result.get("html_url"),
                        },
                    )

                elif action == "search":
                    if not query:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="query is required",
                        )

                    params = {"q": query}
                    response = await client.get(
                        f"{self.base_url}/search/code",
                        params=params,
                    )
                    response.raise_for_status()
                    result = response.json()

                    items = [
                        {
                            "name": i.get("name"),
                            "path": i.get("path"),
                            "repository": i.get("repository", {}).get("full_name"),
                            "url": i.get("html_url"),
                        }
                        for i in result.get("items", [])[:10]
                    ]

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"results": items, "count": len(items)},
                    )

                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Action {action} not supported",
                    )

        except httpx.HTTPStatusError as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"GitHub API error: {e.response.status_code} - {e.response.text}",
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"GitHub operation failed: {str(e)}",
            )
