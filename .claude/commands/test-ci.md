# CI Validation Command

Perform comprehensive CI validation locally before pushing to GitHub.

## Purpose

This command automatically runs the same checks that GitHub Actions CI performs, catching issues before they fail in CI:

1. **Python Services**: Black formatting, Ruff linting, pytest tests
2. **TypeScript Services**: ESLint, TypeScript type checking, production build
3. **Dependencies**: Verify requirements.txt and package.json are up-to-date
4. **Performance**: FDS service performance tests (100ms target)

## Execution Steps

### Step 1: Detect Changed Services

Analyze `git status` to determine which services have modifications:
- services/ecommerce/backend
- services/ecommerce/frontend
- services/fds
- services/ml-service
- services/admin-dashboard/backend
- services/admin-dashboard/frontend

### Step 2: Python Services Validation

For each modified Python service:

1. **Format Code**:
   - Run `black src/` to apply formatting
   - Verify with `black --check src/`

2. **Lint Code**:
   - Run `ruff check src/ --fix` to auto-fix issues
   - Verify with `ruff check src/`

3. **Run Tests**:
   - Unit tests: `pytest tests/unit -v --cov=src`
   - Integration tests: `pytest tests/integration -v`
   - Performance tests (FDS only): `pytest tests/performance -v --benchmark-only`

4. **Check Dependencies**:
   - Verify all imports have corresponding entries in requirements.txt
   - Detect version conflicts with `pip check`

### Step 3: TypeScript Services Validation

For each modified TypeScript service:

1. **Install Dependencies**:
   - Run `npm ci` (clean install)

2. **Lint Code**:
   - Run `npm run lint`

3. **Type Check**:
   - Run `npx tsc --noEmit`

4. **Run Tests** (if available):
   - Run `npm test -- --run --coverage`

5. **Build Production**:
   - Run `npm run build`

### Step 4: Generate Report

Create a summary report with:
- Total checks performed
- Passed checks (with green indicators)
- Failed checks (with error details)
- Recommendations for fixing failures
- Estimated CI pass probability

## Expected Output

```
=== CI Validation Report ===

[MODIFIED] services/ecommerce/backend
  [OK] Black formatting passed
  [OK] Ruff linting passed (3 auto-fixed)
  [OK] Unit tests passed (45 tests, 85% coverage)
  [OK] Integration tests passed (12 tests)
  [OK] Dependencies check passed

[MODIFIED] services/fds
  [OK] Black formatting passed
  [OK] Ruff linting passed
  [OK] Unit tests passed (30 tests, 90% coverage)
  [OK] Performance tests passed (P95: 82ms < 100ms target)

[MODIFIED] services/ecommerce/frontend
  [OK] ESLint passed
  [OK] TypeScript type check passed
  [OK] Production build passed

=== Summary ===
Total: 14 checks
Passed: 14
Failed: 0

[SUCCESS] All CI checks passed! Safe to commit and push.
```

## Failure Handling

If any check fails:

1. **Show detailed error output**
2. **Provide fix suggestions**:
   - Black: "Run 'black src/' to auto-format"
   - Ruff: "Run 'ruff check src/ --fix' to auto-fix"
   - Tests: Show pytest failure details
   - TypeScript: Show tsc error locations

3. **Offer to auto-fix** (if possible):
   - "Do you want me to apply Black formatting now? (yes/no)"
   - "Do you want me to fix Ruff linting issues? (yes/no)"

4. **Block commit** until all checks pass

## Integration with /speckit.implement

This command should be automatically invoked after `/speckit.implement` completes:

```
/speckit.implement
  |
  +-- Execute tasks from tasks.md
  |
  +-- [AUTO] /test-ci
       |
       +-- Validate all changes
       |
       +-- Report results
       |
       +-- Fix issues (if any)
       |
       +-- Ready to commit
```

## Configuration

### Environment Variables (for tests)

Set these in your shell or .env file:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=test_db
export POSTGRES_USER=test_user
export POSTGRES_PASSWORD=test_password
export REDIS_HOST=localhost
export REDIS_PORT=6379
export JWT_SECRET=test_secret_key_for_ci
export ENCRYPTION_KEY=test_encryption_key_32_bytes_!!
export ABUSEIPDB_API_KEY=test_api_key
```

### Docker Services (optional)

Start PostgreSQL and Redis for integration tests:

```bash
docker-compose up -d postgres redis
```

## Performance Targets

- **FDS Service**: P95 < 100ms
- **API Response**: < 200ms
- **Cache Hit Rate**: > 80%
- **Test Coverage**: > 80%

## Exit Codes

- **0**: All checks passed
- **1**: Black formatting failed
- **2**: Ruff linting failed
- **3**: Unit tests failed
- **4**: Integration tests failed
- **5**: TypeScript type check failed
- **6**: ESLint failed
- **7**: Production build failed
- **8**: Dependencies missing

## Usage

### Manual Execution

```bash
/test-ci
```

### Automatic Execution (after /speckit.implement)

Automatically runs after task completion.

### Skip Validation (not recommended)

If you need to skip validation:

```bash
git commit --no-verify -m "WIP: debugging"
```

## Best Practices

1. **Run before every commit**: Catch issues early
2. **Fix auto-fixable issues**: Let tools format/lint automatically
3. **Review test failures**: Don't ignore failing tests
4. **Keep dependencies updated**: Regular `pip check` and `npm audit`
5. **Monitor performance**: FDS must stay under 100ms

## Troubleshooting

### "ModuleNotFoundError" in tests

- **Cause**: Missing dependency in requirements.txt
- **Fix**: `pip install <package>` then `pip freeze | grep <package> >> requirements.txt`

### "Black would reformat"

- **Cause**: Code not formatted
- **Fix**: Run `black src/` to apply formatting

### "Ruff: F401 imported but unused"

- **Cause**: Unused imports
- **Fix**: Run `ruff check src/ --fix` to remove automatically

### "pytest: SQLite does not support UUID"

- **Cause**: Using PostgreSQL-specific UUID type
- **Fix**: Use `from sqlalchemy import Uuid` instead of `from sqlalchemy.dialects.postgresql import UUID`

### "npm ERR! peer dependency"

- **Cause**: Incompatible package versions
- **Fix**: Run `npm install --legacy-peer-deps` or update package.json

## See Also

- GitHub Actions workflows: `.github/workflows/ci-*.yml`
- CLAUDE.md: CI/CD Guidelines section
- pytest.ini: Test configuration
- package.json: Frontend test scripts
