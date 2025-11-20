# Quick Start: Automatic CI Validation

## 5-Minute Setup

### 1. Verify Scripts are Present

Check that validation scripts exist:

```bash
ls .claude/scripts/
# Expected files:
# - auto_validate_ci.py
# - validate_python_service.py
# - validate_typescript_service.py
```

### 2. Test Manual Validation

```bash
# Test the system
python .claude/scripts/auto_validate_ci.py

# Expected output (if no changes):
# [INFO] No modified services detected.
# [SUCCESS] Nothing to validate.
```

### 3. Make a Test Change

```bash
# Make a small change to test validation
echo "# test" >> services/ecommerce/backend/src/models/user.py

# Run validation again
python .claude/scripts/auto_validate_ci.py
```

### 4. Use with /speckit.implement

The validation **automatically runs** after `/speckit.implement`:

```bash
# 1. Execute implementation
/speckit.implement

# 2. System automatically runs CI validation
# (no manual action needed)

# 3. Review results and fix any failures
# (see output for fix suggestions)

# 4. Commit when all checks pass
git add .
git commit -m "feat: implement feature X"
git push
```

### 5. Manual Validation (Alternative)

If you prefer manual control:

```bash
# After making changes
/test-ci

# Or use the script directly
python .claude/scripts/auto_validate_ci.py

# With auto-fix
python .claude/scripts/auto_validate_ci.py --fix-auto
```

## Common Workflows

### Workflow A: Automatic (Recommended)

```
Developer: /speckit.implement
   |
   +-> System executes tasks
   |
   +-> System runs /test-ci (automatic)
   |
   +-> [SUCCESS] -> Developer commits
   |
   +-> [FAILURE] -> Developer fixes -> System re-validates
```

### Workflow B: Manual

```
Developer: /speckit.implement
   |
   +-> System executes tasks
   |
   +-> Developer: /test-ci (manual)
   |
   +-> [SUCCESS] -> Developer commits
   |
   +-> [FAILURE] -> Developer fixes -> Developer runs /test-ci again
```

### Workflow C: Pre-Commit Hook

```bash
# Install pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python .claude/scripts/auto_validate_ci.py
exit $?
EOF

chmod +x .git/hooks/pre-commit

# Now git commit automatically runs validation
git commit -m "feat: new feature"
# -> Validation runs before commit
# -> Commit blocked if validation fails
```

## Quick Fixes

### Fix 1: Black Formatting

```bash
# Problem: "would reformat file.py"
# Solution:
cd services/ecommerce/backend
black src/
```

### Fix 2: Ruff Linting

```bash
# Problem: "F401 imported but unused"
# Solution:
cd services/ecommerce/backend
ruff check src/ --fix
```

### Fix 3: Test Failures

```bash
# Problem: "pytest tests failed"
# Solution: Review test output, fix code
cd services/ecommerce/backend
pytest tests/unit -v  # Run specific test to debug
```

### Fix 4: TypeScript Errors

```bash
# Problem: "Type 'string' is not assignable to type 'number'"
# Solution: Fix type errors in code
cd services/ecommerce/frontend
npx tsc --noEmit  # See detailed errors
```

## Troubleshooting

### Issue: "No module named 'colorama'"

```bash
# Python dependencies missing
pip install colorama
```

### Issue: "npm command not found"

```bash
# Node.js not installed
choco install nodejs  # Windows
```

### Issue: "pytest command not found"

```bash
# pytest not installed
cd services/ecommerce/backend
pip install -r requirements.txt
```

### Issue: "Validation too slow"

```bash
# Run validation for specific service only
python .claude/scripts/validate_python_service.py services/fds
```

## Next Steps

1. **Read full documentation**: `.claude/docs/automatic-ci-validation.md`
2. **Configure settings**: `.claude/config/post-implement-hook.json`
3. **Check CLAUDE.md**: CI/CD Guidelines section
4. **Install pre-commit hook**: For automatic validation on commit

## Support

- **Documentation**: `.claude/docs/automatic-ci-validation.md`
- **Script help**: `python .claude/scripts/auto_validate_ci.py --help`
- **Project guidelines**: `CLAUDE.md` (CI/CD Guidelines section)

## Expected Results

After setup:

- [CHECK] CI pass rate: 95%+ (up from 40%)
- [CHECK] Faster development: Catch issues in < 5 min (vs. 10-15 min in CI)
- [CHECK] Fewer fix commits: 0-1 per PR (vs. 3-5)
- [CHECK] Better code quality: Consistent enforcement

Happy coding!
