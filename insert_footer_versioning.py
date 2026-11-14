#!/usr/bin/env python3
"""
insert_footer_versioning.py

Inserts an auto-versioning JavaScript function into the footer (immediately before </body>)
of all HTML files. On page load, this function generates a fresh version number (timestamp)
and updates URLs for styles.css, styles.min.css, and script.js.
"""

import os
import sys

FOOTER_SCRIPT = """  <!-- Auto-version styles and scripts on page load -->
  <script>
    (function () {
      try {
        var version = Date.now();
        var targetPattern = /(styles\\.css|styles\\.min\\.css|script\\.js)/i;

        // Update stylesheet & preload links
        var links = document.querySelectorAll('link[rel="stylesheet"], link[as="style"]');
        for (var i = 0; i < links.length; i++) {
          var href = links[i].getAttribute('href');
          if (href && targetPattern.test(href)) {
            links[i].setAttribute('href', href.split('?')[0] + '?v=' + version);
          }
        }

        // Update script tags
        var scripts = document.querySelectorAll('script[src]');
        for (var j = 0; j < scripts.length; j++) {
          var src = scripts[j].getAttribute('src');
          if (src && targetPattern.test(src)) {
            scripts[j].setAttribute('src', src.split('?')[0] + '?v=' + version);
          }
        }
      } catch (e) {
        console.error('Error auto-versioning assets:', e);
      }
    })();
  </script>
</body>"""

EXCLUDE_DIRS = {'.git', '.vscode', 'node_modules', 'scratch', 'brain'}

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    updated_files = 0
    skipped_files = 0
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            if not filename.lower().endswith('.html'):
                continue

            total_files += 1
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {rel_path}: {e}")
                continue

            # Skip if already inserted
            if '<!-- Auto-version styles and scripts on page load -->' in content:
                skipped_files += 1
                continue

            # Check if </body> exists
            if '</body>' not in content:
                print(f"Warning: No </body> found in {rel_path}")
                continue

            # Replace the last occurrence of </body>
            # (or exact </body> since each file has only one)
            new_content = content.replace('</body>', FOOTER_SCRIPT, 1)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            updated_files += 1

    print("=" * 50)
    print("Footer Script Insertion Complete!")
    print(f"Total HTML files scanned : {total_files}")
    print(f"Files updated            : {updated_files}")
    print(f"Files already had script : {skipped_files}")
    print("=" * 50)

if __name__ == '__main__':
    main()
