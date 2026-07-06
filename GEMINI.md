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
