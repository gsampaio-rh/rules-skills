# Security Patterns — Full Reference

## Input Validation
- **Backend**: validate all inputs at API boundaries (Pydantic, Zod, JSON Schema)
- **Frontend**: validate user inputs before sending to API
- **Sanitization**: sanitize user inputs before LLM prompts (prevent prompt injection)
- **Rate limiting**: rate limit public-facing API endpoints

## Authentication & Authorization
- **Authenticate all API requests**: JWT, OAuth, or API keys
- **Store tokens securely**: httpOnly cookies preferred over localStorage
- **Least privilege**: minimum permissions required for each operation
- **Audit logs**: log access to sensitive resources

## Data Protection
- **Encryption at rest**: encrypt sensitive data in storage
- **TLS/HTTPS**: enforce for all data in transit
- **PII masking**: mask PII in logs and error messages
- **Secrets management**: never store secrets in source code; use environment variables or vault

## Data & Notebook Security
- **No raw data in git**: add `data/` to `.gitignore`. Use DVC or cloud storage for large datasets.
- **No PII in notebooks**: mask or anonymize sensitive fields before analysis
- **No credentials in notebooks**: use environment variables or config files, never inline API keys or passwords
- **Mask sensitive output**: redact PII from notebook outputs before sharing or committing
- **`.env` files**: never commit. Add to `.gitignore`.

## Frontend Security
- **XSS prevention**: sanitize user-generated content before rendering
- **CSRF protection**: use CSRF tokens for state-changing operations
- **CSP**: implement Content Security Policy headers
- **API keys**: never expose in frontend code (use backend proxy)

## Dependency Security
- **Vulnerability scanning**: `pip-audit`, `npm audit`, or Snyk in CI
- **Regular updates**: keep dependencies current, review changelogs for security fixes
- **Pin versions**: use lockfiles (`poetry.lock`, `package-lock.json`, `uv.lock`)

## Supply Chain Defense
- **Minimize dependencies**: before adding a package, evaluate if the functionality can be implemented directly. Fewer deps = smaller attack surface.
- **Audit before installing**: inspect a package's dependencies, install scripts, and download stats before adding it. Use `npm-inspect`, `uv-inspect`, or check on socket.dev.
- **npm: block install scripts**: global `ignore-scripts=true` in `~/.npmrc` prevents postinstall malware. Run `npm rebuild <pkg>` manually for legitimate native builds.
- **npm: pin exact versions**: global `save-exact=true` in `~/.npmrc` prevents `^` ranges from pulling compromised newer versions.
- **uv: exclude-newer cooldown**: global `exclude-newer = "3 days"` in `~/.config/uv/uv.toml` ignores packages published in the last 3 days.
- **pip: require virtualenvs**: global `require-virtualenv=true` in pip.conf prevents installing into the system Python.
- **CI/CD: pin by hash, not tag**: GitHub Actions tags can be hijacked. Use `actions/checkout@<sha>` instead of `@v4`.
- **CI/CD: use frozen installs**: `npm ci`, `uv sync --frozen`, `pip install --require-hashes` — never resolve fresh in production pipelines.
- **Review lockfile diffs**: treat lockfile changes in PRs with the same scrutiny as code changes. New transitive dependencies are the primary attack vector.
- **Block known-compromised versions**: use `constraint-dependencies` in `pyproject.toml` for Python. No npm equivalent — rely on `npm audit` + lockfile review.

## Environment Isolation
- **Develop in containers**: devcontainers or Docker isolate your credentials from malicious install scripts
- **Limit credential exposure**: use secrets managers (`aws-vault`, `op run`), not env vars in shell profiles
- **SSH keys with passphrase**: use `ssh-add -t 3600` for time-limited agent sessions
- **Rotate credentials**: especially after any suspected compromise or package incident
