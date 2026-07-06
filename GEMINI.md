# Gemini 3.1 Pro Specific Rules
**CRITICAL: STRICT NATIVE TOOLS ONLY FOR FILE OPERATIONS**: You are strictly FORBIDDEN from using the `run_command` tool with shell utilities (like `grep`, `sed`, `awk`, `cat`, `ls`, `find`, or inline python scripts) for text replacement, file reading, or searching.
You MUST use ONLY the native API tools provided by the environment:
1. `view_file` (to read lines from a file)
2. `edit_file` (to replace a contiguous block of text)
3. `multi_edit_file` (to replace multiple text blocks at once)
4. `create_file` (to create new files)
5. `delete_file` (to delete files)
6. `list_dir` (to view contents of directories)
7. `move` (to rename or move files/directories)

DO NOT automate text processing with shell scripts. Use the native tools to open, read, and write to files.

## LaTeX Formatting & \mycode Rule
- **Use `\mycode{...}` instead of raw `\texttt` or manual escaping (`\_`)**: When writing file names, directory paths, Python variables, or short inline code snippets in the LaTeX files, always use the centralized `\mycode{...}` macro defined in `myconfig.sty`.
- **No manual escaping is needed inside `\mycode`**: Inside `\mycode{...}`, write symbols like underscores directly (e.g., `\mycode{data_loader.py}`, `\mycode{normalize_angle}`). Do not write `\_` inside `\mycode`. Unescaped underscores outside of `\mycode` or math mode will cause LaTeX compilation errors.
