# Google Python Style Guide

*This document is based on the Google Python Style Guide and has been added to provide comprehensive coding standards for this project.*

## Table of Contents

1. [Background](#background)
2. [Python Language Rules](#python-language-rules)
3. [Python Style Rules](#python-style-rules)
4. [Project-Specific Additions](#project-specific-additions)
5. [Parting Words](#parting-words)

## 1. Background

Python is the main dynamic language used at Google. This style guide is a list of *dos and don'ts* for Python programs.

The guide recommends using Black or Pyink auto-formatter to avoid formatting debates. **Note: This project uses Black with 88-character line limit as configured in `pyproject.toml`.**

## 2. Python Language Rules

### 2.1 Lint

**Decision**: Make sure you run `pylint` on your code using the provided configuration.

**Project Note**: This project uses `flake8` instead of `pylint`, configured in `.flake8`.

Use line-level comments to suppress inappropriate warnings:
```python
def do_PUT(self):  # WSGI name, so pylint: disable=invalid-name
```

For unused arguments, delete variables at function start with explanatory comments:
```python
def viking_cafe_order(spam: str, beans: str, eggs: str | None = None) -> str:
    del beans, eggs  # Unused by vikings.
    return spam + spam + spam
```

### 2.2 Imports

**Decision**: Use `import` statements for packages and modules only, not for individual types, classes, or functions.

**Allowed patterns**:
- `import x` for packages and modules
- `from x import y` where x is package prefix, y is module name
- `from x import y as z` for conflicts or long names
- `import y as z` only for standard abbreviations (e.g., `import numpy as np`)

**Examples**:
```python
# Yes
from sound.effects import echo
echo.EchoFilter(input, output, delay=0.7, atten=4)

# No - relative imports
import jodie  # Unclear which jodie module
```

**Exemptions**: Symbols from `typing`, `collections.abc`, `typing_extensions`, and `six.moves` modules.

### 2.3 Packages

**Decision**: All new code should import each module by its full package name.

```python
# Yes
import absl.flags
from doctor.who import jodie

# No
import jodie  # Ambiguous
```

### 2.4 Exceptions

**Decision**: Exceptions must follow certain conditions:

- Use built-in exception classes when appropriate
- Don't use `assert` for critical application logic
- Inherit custom exceptions from existing exception classes
- Never use catch-all `except:` statements
- Minimize code in `try`/`except` blocks

```python
# Yes
def connect_to_next_port(self, minimum: int) -> int:
    if minimum < 1024:
        raise ValueError(f'Min. port must be at least 1024, not {minimum}.')
    # Implementation continues...

# No
def connect_to_next_port(self, minimum: int) -> int:
    assert minimum >= 1024, 'Minimum port must be at least 1024.'
```

### 2.5 Mutable Global State

**Decision**: Avoid mutable global state.

When necessary, make global entities internal with `_` prefix and provide public access through functions or class methods.

### 2.6 Nested/Local/Inner Classes and Functions

**Decision**: They are fine with some caveats. Avoid nested functions or classes except when closing over a local value other than `self` or `cls`.

### 2.7 Comprehensions & Generator Expressions

**Decision**: Comprehensions are allowed, however multiple `for` clauses or filter expressions are not permitted.

```python
# Yes
result = [mapping_expr for value in iterable if filter_expr]

# No
result = [(x, y) for x in range(10) for y in range(5) if x * y > 10]
```

### 2.8 Default Iterators and Operators

**Decision**: Use default iterators and operators for types that support them.

```python
# Yes
for key in adict: ...
if obj in alist: ...

# No
for key in adict.keys(): ...
```

### 2.9 Generators

**Decision**: Fine. Use "Yields:" rather than "Returns:" in the docstring for generator functions.

### 2.10 Lambda Functions

**Decision**: Okay for one-liners. Prefer generator expressions over `map()` or `filter()` with a `lambda`.

### 2.11 Conditional Expressions

**Decision**: Okay to use for simple cases. Each portion must fit on one line.

```python
# Yes
one_line = 'yes' if predicate(value) else 'no'

# No
bad_line_breaking = ('yes' if predicate(value) else
                     'no')
```

### 2.12 Default Argument Values

**Decision**: Do not use mutable objects as default values in the function or method definition.

```python
# Yes
def foo(a, b=None):
    if b is None:
        b = []

# No
def foo(a, b=[]):
    ...
```

### 2.13 Properties

**Decision**: Properties are allowed for trivial computations that match regular attribute access expectations. Use `@property` decorator.

### 2.14 True/False Evaluations

**Decision**: Use the "implicit" false if possible.

```python
# Yes
if foo:  # instead of if foo != []
if foo is None:  # for None checks

# No
if len(users) == 0:
```

### 2.16 Lexical Scoping

**Decision**: Okay to use, but be aware of potential confusing bugs with variable binding.

### 2.17 Function and Method Decorators

**Decision**: Use decorators judiciously when there is a clear advantage. Avoid `staticmethod` and limit use of `classmethod`.

Write module-level functions instead of `staticmethod`. Use `classmethod` only for named constructors or class-specific routines.

### 2.18 Threading

Do not rely on the atomicity of built-in types. Use `queue.Queue` for thread communication and proper locking primitives.

### 2.19 Power Features

**Decision**: Avoid these features in your code including metaclasses, bytecode access, dynamic inheritance, etc.

### 2.20 Modern Python: from __future__ imports

**Decision**: Use of `from __future__ import` statements is encouraged.

### 2.21 Type Annotated Code

**Decision**: You are strongly encouraged to enable Python type analysis when updating code.

**Project Note**: This project uses MyPy for type checking, configured in `pyproject.toml`.

## 3. Python Style Rules

### 3.1 Semicolons

**Decision**: Do not terminate your lines with semicolons, and do not use semicolons to put two statements on the same line.

### 3.2 Line Length

**Decision**: Maximum line length is *80 characters*.

**Project Note**: This project uses Black with 88-character line limit as configured in `pyproject.toml`, which is acceptable and widely adopted.

Use implicit line joining with parentheses instead of backslashes:

```python
# Yes
foo_bar(self, width, height, color='black', design=None, x='foo',
        emphasis=None, highlight=0)

# No
if width == 0 and height == 0 and \
        color == 'red' and emphasis == 'strong':
```

### 3.3 Parentheses

**Decision**: Use parentheses sparingly.

```python
# Yes
if foo:
    bar()
return foo

# No
if (x):
    bar()
return (foo)
```

### 3.4 Indentation

**Decision**: Indent your code blocks with *4 spaces*.

```python
# Yes - Aligned with opening delimiter
foo = long_function_name(var_one, var_two,
                         var_three, var_four)

# Yes - 4-space hanging indent
foo = long_function_name(
    var_one, var_two, var_three,
    var_four)
```

#### 3.4.1 Trailing Commas

Use trailing commas when closing container token is on different line than final element.

### 3.5 Blank Lines

Two blank lines between top-level definitions, one blank line between method definitions.

### 3.6 Whitespace

**Standard rules**:
- No whitespace inside parentheses, brackets, or braces
- No whitespace before comma, semicolon, or colon
- Surround binary operators with single spaces
- No spaces around `=` for keyword arguments (except with type annotations)

```python
# Yes
spam(ham[1], {'eggs': 2}, [])
def complex(real, imag: float = 0.0): return Magic(r=real, i=imag)

# No
spam( ham[ 1 ], { 'eggs': 2 }, [ ] )
def complex(real, imag: float=0.0): return Magic(r = real, i = imag)
```

### 3.7 Shebang Line

Use `#!/usr/bin/env python3` or `#!/usr/bin/python3` for executable files.

### 3.8 Comments and Docstrings

#### 3.8.1 Docstrings

Always use the three-double-quote `"""` format for docstrings. Start with summary line not exceeding 80 characters.

#### 3.8.2 Modules

Every file should contain license boilerplate and module docstring:

```python
"""A one-line summary of the module or program, terminated by a period.

Leave one blank line.  The rest of this docstring should contain an
overall description of the module or program.
"""
```

#### 3.8.3 Functions and Methods

Document functions with one or more of:
- Part of public API
- Nontrivial size
- Non-obvious logic

Use sections: `Args:`, `Returns:`, `Raises:`

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows from a Smalltable.

    Args:
        table_handle: An open smalltable.Table instance.
        keys: A sequence of strings representing the key of each table
          row to fetch.

    Returns:
        A dict mapping keys to the corresponding table row data.

    Raises:
        IOError: An error occurred accessing the smalltable.
    """
```

### 3.10 Strings

**Decision**: Use an f-string, the `%` operator, or the `format` method for formatting strings.

```python
# Yes
x = f'name: {name}; score: {n}'
x = 'name: %s; score: %d' % (name, n)

# No
x = 'name: ' + name + '; score: ' + str(n)
```

Use `''.join()` for string accumulation in loops, not `+=`.

#### 3.10.1 Logging

Always call them with a string literal (not an f-string!) as their first argument with pattern-parameters as subsequent arguments.

```python
# Yes
logging.info('TensorFlow Version is: %s', tf.__version__)

# No
logging.info(f'Cannot write to home directory, $HOME={homedir!r}')
```

### 3.11 Files, Sockets, and similar Stateful Resources

Explicitly close files and sockets when done with them. Use `with` statements:

```python
with open("hello.txt") as hello_file:
    for line in hello_file:
        print(line)
```

### 3.12 TODO Comments

Format: `# TODO: crbug.com/192795 - Investigate cpufreq optimizations.`

### 3.13 Imports Formatting

**Project Note**: This project uses `isort` for import formatting, configured in `pyproject.toml`.

Import order:
1. Python future imports
2. Python standard library
3. Third-party modules
4. Code repository sub-packages

```python
import collections
import sys

from absl import app
import tensorflow as tf

from myproject.backend import huxley
```

### 3.14 Statements

**Decision**: Generally only one statement per line.

```python
# Yes
if foo: bar(foo)

# No
if foo: bar(foo)
else:   baz(foo)
```

### 3.15 Getters and Setters

Use when getting/setting provides meaningful behavior or significant cost. Follow naming: `get_foo()`, `set_foo()`.

### 3.16 Naming

**Conventions**: `module_name`, `ClassName`, `method_name`, `GLOBAL_CONSTANT_NAME`

#### 3.16.1 Names to Avoid

- Single character names (except counters, exceptions, file handles)
- Dashes in package/module names
- `__double_leading_and_trailing_underscore__` names
- Names that include variable type unnecessarily

#### 3.16.2 Naming Conventions

| Type | Public | Internal |
|------|--------|----------|
| Packages | `lower_with_under` | |
| Modules | `lower_with_under` | `_lower_with_under` |
| Classes | `CapWords` | `_CapWords` |
| Functions | `lower_with_under()` | `_lower_with_under()` |
| Constants | `CAPS_WITH_UNDER` | `_CAPS_WITH_UNDER` |
| Variables | `lower_with_under` | `_lower_with_under` |

### 3.17 Main

```python
def main():
    ...

if __name__ == '__main__':
    main()
```

### 3.18 Function Length

Prefer small and focused functions. No hard limit, but consider breaking up functions exceeding ~40 lines.

### 3.19 Type Annotations

#### 3.19.1 General Rules

- At least annotate your public APIs
- Annotating `self`/`cls` generally not necessary
- Use `Any` when type cannot be expressed
- Not required to annotate all functions

**Project Note**: This project encourages type annotations and uses MyPy for type checking.

#### 3.19.2 Line Breaking

```python
def my_method(
    self,
    first_var: int,
    second_var: Foo,
    third_var: Bar | None,
) -> int:
    ...
```

#### 3.19.4 Default Values

Use spaces around the `=` *only* for arguments that have both a type annotation and a default value.

#### 3.19.5 NoneType

Use explicit `X | None` instead of implicit.

```python
# Yes
def modern_or_union(a: str | None = None) -> str:
    ...

# No
def implicit_optional(a: str = None) -> str:
    ...
```

#### 3.19.12 Imports For Typing

```python
from collections.abc import Mapping, Sequence
from typing import Any, Generic, cast, TYPE_CHECKING
```

## 4. Project-Specific Additions

### 4.1 Existing Tooling

This project already has comprehensive tooling configured:

- **Black**: Code formatting (88-character line limit)
- **Flake8**: Linting with configuration in `.flake8`
- **MyPy**: Type checking configured in `pyproject.toml`
- **isort**: Import sorting configured in `pyproject.toml`
- **Pre-commit hooks**: Automated quality checks including:
  - Code formatting and linting
  - Type checking
  - Security scanning (Bandit, Safety)
  - Secrets detection
  - Docker and Markdown linting

### 4.2 Testing Standards

- Use **pytest** for all tests
- Achieve 92%+ code coverage (currently 92.41%, configured in `pyproject.toml`)
- Place tests in the `/tests/` directory
- Follow naming convention: `test_*.py` for test files

### 4.3 Project Structure

Follow the established project structure:
- Source code in `/src/` directory
- Tests in `/tests/` directory
- Requirements split by environment in `/requirements/` directory
- Documentation in `/docs/` directory (new)

### 4.4 Logging

This project uses Python's standard logging module. Follow these conventions:
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Use string formatting with parameters (not f-strings) as per section 3.10.1
- Configure logging in the main application entry point

### 4.5 Error Handling

For this bank statement processing application:
- Handle PDF parsing errors gracefully
- Provide meaningful error messages for file I/O operations
- Log errors appropriately for debugging
- Use specific exception types when possible

## 5. Parting Words

The style guide emphasizes consistency, readability, and maintainability while acknowledging that "consistency within a project is more important" than strict adherence when conflicts arise.

**For this project specifically**: The existing pre-commit hooks and automated tooling already enforce many of these standards. This guide serves as comprehensive documentation of coding practices and should be used alongside the automated tooling to ensure high-quality, consistent code.

---

*Sources:*
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)