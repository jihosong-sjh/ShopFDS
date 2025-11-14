#!/usr/bin/env python3
"""
Fix absolute imports to use src. prefix
"""
import re
from pathlib import Path


def fix_imports_in_file(file_path: Path):
    """Fix imports in a single file"""
    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # Replace patterns
    patterns = [
        (r'^from models\.', 'from src.models.'),
        (r'^from services\.', 'from src.services.'),
        (r'^from middleware\.', 'from src.middleware.'),
        (r'^from utils\.', 'from src.utils.'),
        (r'^from api\.', 'from src.api.'),
        (r'^from config import', 'from src.config import'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print(f"Fixed: {file_path}")
        return True
    return False


def main():
    """Main function"""
    src_dir = Path(__file__).parent / 'src'

    # Find all Python files
    python_files = list(src_dir.rglob('*.py'))

    fixed_count = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == '__main__':
    main()
