# Gemini 3.1 Pro Specific Rules
- **SHELL COMMANDS**: Executing shell commands using `run_command` is permitted for file operations and other tasks as needed.


## LaTeX Formatting & \mycode Rule
- **Use `\mycode{...}` instead of raw `\texttt` or manual escaping (`\_`)**: When writing file names, directory paths, Python variables, or short inline code snippets in the LaTeX files, always use the centralized `\mycode{...}` macro defined in `myconfig.sty`.
- **No manual escaping is needed inside `\mycode`**: Inside `\mycode{...}`, write symbols like underscores directly (e.g., `\mycode{data_loader.py}`, `\mycode{normalize_angle}`). Do not write `\_` inside `\mycode`. Unescaped underscores outside of `\mycode` or math mode will cause LaTeX compilation errors.

## Incremental Config.py Filling (CRITICAL)
- **Keep `config.py` in Section 2 Minimal**: The configuration module `config.py` in Section 2 (Listing 5) MUST remain minimal and only contain settings introduced up to that point (i.e., paths and directories).
- **No full config copy-pasting in early chapters**: Do not duplicate the entire, final config file in early sections of the book.
- **Instruct rather than re-paste**: When new configuration parameters (like DSP parameters in Section 4 or polarizer variables in Sections 6-8) are needed, do NOT re-paste or show a complete `config.py` listing. Instead, write clear instructions telling the student which specific lines of code to append/add to their existing `config.py` file. The final complete config script is only loaded dynamically in the Appendix.

## Uniform Code Breakdown Standard (CRITICAL)
- **Always isolate code analyses**: When presenting detailed explanations of code listings, place them inside a dedicated level-3 subsection: `\subsubsection{Разбор кода}` (or `\subsubsection{Разбор кода: Тема/Имя файла}`).
- **Use the `syntaxdesc` list environment**: For describing syntax, variable roles, parameters, or operators, you MUST strictly use the customized `syntaxdesc` environment defined in `myconfig.sty`:
- **Label Formatting Rule**: Every item's label in `syntaxdesc` MUST use a combined, contextual format containing BOTH the programmatic/logical role of the element and the exact code snippet:
  ```latex
  \begin{syntaxdesc}
      \item[Имя переменной \mycode{variable_name}] Описание роли переменной в контексте.
      \item[Параметр функции \mycode{param_name: type}] Описание параметра функции.
  \end{syntaxdesc}
  ```
- **Do not use bullet/numbered lists, raw paragraph runs, purely abstract roles (e.g., `\item[Имя функции]`), or purely code items (e.g., `\item[\mycode{variable}]`) for syntax explanations.** Keep all items organized with descriptive bracket labels containing both the role and code exactly as shown above.


