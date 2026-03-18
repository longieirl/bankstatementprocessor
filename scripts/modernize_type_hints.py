#!/usr/bin/env python3
"""Script to modernize type hints across the codebase.

This script:
1. Adds 'from __future__ import annotations' to all Python files
2. Updates typing imports to remove unnecessary ones with PEP 604 style
3. Modernizes type hints:
   - Optional[X] -> X | None
   - Union[X, Y] -> X | Y
   - List[X] -> list[X]
   - Dict[K, V] -> dict[K, V]
   - Tuple[X, Y] -> tuple[X, Y]
   - Set[X] -> set[X]
"""

import re
import sys
from pathlib import Path
from typing import List, Set


def add_future_annotations(content: str, filepath: Path) -> tuple[str, bool]:
    """Add 'from __future__ import annotations' if not present."""
    if "from __future__ import annotations" in content:
        return content, False

    lines = content.split("\n")

    # Find where to insert (after docstring, shebang, or at top)
    insert_index = 0
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip shebang
        if i == 0 and stripped.startswith("#!"):
            insert_index = i + 1
            continue

        # Track docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                docstring_char = stripped[:3]
                in_docstring = True
                if stripped.endswith(docstring_char) and len(stripped) > 6:
                    # Single-line docstring
                    in_docstring = False
                    insert_index = i + 1
            elif stripped.endswith(docstring_char):
                in_docstring = False
                insert_index = i + 1
            continue

        # Skip empty lines and encoding declarations at top
        if not stripped or stripped.startswith("#") and i < 3:
            if not in_docstring:
                insert_index = i + 1
            continue

        # Found first real line
        if not in_docstring:
            break

    # Insert the import
    lines.insert(insert_index, "from __future__ import annotations")
    lines.insert(insert_index + 1, "")

    return "\n".join(lines), True


def modernize_optional(content: str) -> tuple[str, int]:
    """Convert Optional[X] to X | None."""
    count = 0

    # Optional[X] -> X | None
    pattern = r'Optional\[([^\[\]]+(?:\[[^\]]+\])?)\]'

    def replace_optional(match):
        nonlocal count
        count += 1
        return f"{match.group(1)} | None"

    content = re.sub(pattern, replace_optional, content)

    return content, count


def modernize_union(content: str) -> tuple[str, int]:
    """Convert Union[X, Y] to X | Y."""
    count = 0

    # Union[X, Y] -> X | Y
    pattern = r'Union\[([^\[\]]+(?:\[[^\]]+\])?(?:,\s*[^\[\]]+(?:\[[^\]]+\])?)+)\]'

    def replace_union(match):
        nonlocal count
        count += 1
        types = [t.strip() for t in match.group(1).split(',')]
        return ' | '.join(types)

    content = re.sub(pattern, replace_union, content)

    return content, count


def modernize_collections(content: str) -> tuple[str, int]:
    """Convert List[X], Dict[K,V], etc. to lowercase generics."""
    count = 0

    replacements = {
        'List': 'list',
        'Dict': 'dict',
        'Set': 'set',
        'Tuple': 'tuple',
        'FrozenSet': 'frozenset',
    }

    for old, new in replacements.items():
        pattern = rf'\b{old}\['
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, f'{new}[', content)
            count += matches

    return content, count


def remove_unused_typing_imports(content: str) -> tuple[str, Set[str]]:
    """Remove typing imports that are no longer needed."""
    removed = set()

    # Types that are no longer needed with PEP 604 and built-in generics
    potentially_unused = {'List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union', 'FrozenSet'}

    # Check which types are still used in the file
    still_used = set()
    for type_name in potentially_unused:
        # Check if type is used outside of import line
        if re.search(rf'\b{type_name}\b(?!.*from typing import)', content):
            still_used.add(type_name)

    # Remove unused imports
    import_pattern = r'from typing import ([^\n]+)'

    def clean_imports(match):
        imports = [i.strip() for i in match.group(1).split(',')]
        kept_imports = []

        for imp in imports:
            # Remove type parameter (e.g., "List" from "List[X]")
            base_type = imp.split('[')[0].strip()

            if base_type in potentially_unused and base_type not in still_used:
                removed.add(base_type)
            else:
                kept_imports.append(imp)

        if not kept_imports:
            return ''  # Remove entire import line if nothing left

        return f"from typing import {', '.join(kept_imports)}"

    content = re.sub(import_pattern, clean_imports, content)

    # Remove empty import lines
    content = re.sub(r'\nfrom typing import \n', '\n', content)
    content = re.sub(r'\nfrom typing import $', '', content, flags=re.MULTILINE)

    return content, removed


def process_file(filepath: Path) -> dict:
    """Process a single Python file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        stats = {
            'future_added': False,
            'optional_count': 0,
            'union_count': 0,
            'collection_count': 0,
            'removed_imports': set(),
        }

        # Add future annotations first
        content, stats['future_added'] = add_future_annotations(content, filepath)

        # Modernize type hints
        content, stats['optional_count'] = modernize_optional(content)
        content, stats['union_count'] = modernize_union(content)
        content, stats['collection_count'] = modernize_collections(content)

        # Remove unused imports (do this last)
        content, stats['removed_imports'] = remove_unused_typing_imports(content)

        # Write back if changed
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            stats['modified'] = True
        else:
            stats['modified'] = False

        return stats

    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return {'error': str(e)}


def main():
    """Main entry point."""
    root = Path(__file__).parent.parent

    # Find all Python files
    python_files = []
    for pattern in ['src/**/*.py', 'tests/**/*.py']:
        python_files.extend(root.glob(pattern))

    # Filter out __pycache__
    python_files = [f for f in python_files if '__pycache__' not in str(f)]

    print(f"Found {len(python_files)} Python files to process")

    total_stats = {
        'files_modified': 0,
        'future_added': 0,
        'optional_count': 0,
        'union_count': 0,
        'collection_count': 0,
        'errors': 0,
    }

    for filepath in sorted(python_files):
        stats = process_file(filepath)

        if 'error' in stats:
            total_stats['errors'] += 1
            continue

        if stats['modified']:
            total_stats['files_modified'] += 1
            if stats['future_added']:
                total_stats['future_added'] += 1
            total_stats['optional_count'] += stats['optional_count']
            total_stats['union_count'] += stats['union_count']
            total_stats['collection_count'] += stats['collection_count']

            print(f"✓ {filepath.relative_to(root)}")

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Files modified: {total_stats['files_modified']}")
    print(f"  Future annotations added: {total_stats['future_added']}")
    print(f"  Optional[X] → X | None: {total_stats['optional_count']}")
    print(f"  Union[X, Y] → X | Y: {total_stats['union_count']}")
    print(f"  List/Dict/etc → list/dict/etc: {total_stats['collection_count']}")
    print(f"  Errors: {total_stats['errors']}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
