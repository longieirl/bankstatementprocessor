# Security Policy

## Scope

This policy covers the `longieirl/bankstatementprocessor` repository.

## Reporting a vulnerability

Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/longieirl/bankstatementprocessor/security/advisories/new).

Include:
- Description of the vulnerability
- Steps to reproduce
- Affected versions or files
- Potential impact

Do not open a public issue for security vulnerabilities.

**Expected response:** acknowledgement within 7 days, resolution timeline within 30 days.

## Push protection bypass policy

Secret scanning push protection can be bypassed by users with write access. This is not permitted unless the detected secret is a confirmed false positive. Any bypass must be reviewed by the repository owner. Bypass events are logged in the repository audit log.

## Branch ruleset bypass policy

The branch ruleset includes a bypass actor (Repository Admin, actor_id 5) with `bypass_mode: pull_request`. This allows the sole owner to merge pull requests — including bot-generated Dependabot PRs — without a second reviewer. Direct pushes to `main` remain blocked even for the bypass actor. This tradeoff is intentional for a solo-owner repository where requiring a second reviewer would create a permanent deadlock.

## Known accepted risks

<!-- Document accepted patterns here so reviewers do not re-flag them. -->
<!-- Example: Docker socket mount required for Watchtower; NET_ADMIN required for WireGuard -->
