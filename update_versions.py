#!/usr/bin/env python3
"""
update_versions.py

Batch asset version updater for cache busting.
Automatically detects and updates query version strings (?v=...)
for styles.css, styles.min.css, and script.js across all HTML files.

Usage:
    python update_versions.py                  # Defaults to current date: YYYYMMDD (e.g., 20261114)
    python update_versions.py 1.0.2            # Custom version
    python update_versions.py --dry-run        # Preview changes without modifying files
"""

import sys
import os
import re
from datetime import datetime

# Regex matching href or src attributes referencing target files
# Supports existing query parameters like ?16161616, ?v=1, ?ver=0.0.1, or no query param
ASSET_PATTERN = re.compile(
    r'(?P<attr>\b(?:href|src)=)(?P<quote>["\']?)(?P<path>[^"\'\s>]*?(?:styles\.css|styles\.min\.css|script\.js))(?:\?[^"\'\s>]*)?(?P=quote)',
    re.IGNORECASE
)

# Directories to skip
EXCLUDE_DIRS = {'.git', '.vscode', 'node_modules', 'scratch', 'brain'}

def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    flags = [arg for arg in sys.argv[1:] if arg.startswith('--')]

    dry_run = '--dry-run' in flags

    # Determine version string
    if args:
        version = args[0]
    else:
        version = datetime.now().strftime('%Y%m%d')

    print(f"{'[DRY RUN] ' if dry_run else ''}Updating asset URLs to ?v={version} across all HTML files...\n")

    total_files_scanned = 0
    updated_files_count = 0
    total_replacements = 0

    root_dir = os.path.dirname(os.path.abspath(__file__))

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude unwanted directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            if not filename.lower().endswith('.html'):
                continue

            total_files_scanned += 1
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {rel_path}: {e}")
                continue

            file_matches = 0

            def replacer(match):
                nonlocal file_matches
                file_matches += 1
                attr = match.group('attr')
                quote = match.group('quote') or '"'
                path = match.group('path')
                return f"{attr}{quote}{path}?v={version}{quote}"

            new_content = ASSET_PATTERN.sub(replacer, content)

            if file_matches > 0 and new_content != content:
                updated_files_count += 1
                total_replacements += file_matches
                if not dry_run:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                print(f"  {'[WOULD UPDATE]' if dry_run else '[UPDATED]'} {rel_path} ({file_matches} references)")

    print("\n" + "=" * 50)
    print(f"Scan complete!")
    print(f"Total HTML files scanned : {total_files_scanned}")
    print(f"Files updated            : {updated_files_count}")
    print(f"Total asset URLs versioned: {total_replacements}")
    print(f"Applied version query    : ?v={version}")
    print("=" * 50)

if __name__ == '__main__':
    main()
