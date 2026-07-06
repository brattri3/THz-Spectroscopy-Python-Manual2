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

## Incremental Config.py Filling (CRITICAL)
- **Keep `config.py` in Section 2 Minimal**: The configuration module `config.py` in Section 2 (Listing 5) MUST remain minimal and only contain settings introduced up to that point (i.e., paths and directories).
- **No full config copy-pasting in early chapters**: Do not duplicate the entire, final config file in early sections of the book.
- **Instruct rather than re-paste**: When new configuration parameters (like DSP parameters in Section 4 or polarizer variables in Sections 6-8) are needed, do NOT re-paste or show a complete `config.py` listing. Instead, write clear instructions telling the student which specific lines of code to append/add to their existing `config.py` file. The final complete config script is only loaded dynamically in the Appendix.

