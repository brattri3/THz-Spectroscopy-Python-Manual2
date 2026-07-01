# Terahertz Spectroscopy with Python: An Engineering Tutorial

This repository contains the source code and LaTeX files for a comprehensive methodological guide on processing Terahertz (THz) spectroscopy data using Python.

## 🎯 Project Overview
This guide is designed for engineering students and researchers who want to learn Python by solving a real-world scientific problem. It walks the reader through:
- Setting up the Python environment and development tools.
- Loading and parsing experimental data.
- Digital Signal Processing (DSP) fundamentals: removing DC bias, applying Gaussian windows, and Fast Fourier Transform (FFT).
- Fitting experimental data to the theoretical Blanco model for wire-grid polarizers.
- Optimizing parameters and analyzing frequency dependencies.

## 🏗️ Repository Structure
- `/text/` - Contains all the `.tex` files, structural configuration (`myconfig.sty`), and chapters of the manual.
- `/text/images/` - (To be created) Directory for screenshots and plots. LaTeX automatically detects images here using the `\smartfigure` command.
- `AGENTS.md` & `manifest.md` - System instructions and pedagogical frameworks (Tell, Show, Do, Review) driving the creation of this manual.

## 🛠️ Building the Document
The manual is written in LaTeX and strictly uses the `minted` package for syntax highlighting.

**Requirements:**
- A LaTeX distribution (TeX Live, MiKTeX, etc.)
- Python with the `Pygments` library installed (required for `minted`).

**Compilation Command:**
```bash
xelatex --shell-escape main.tex
```
*(Run this command from inside the `/text/` directory. You may need to run it twice to resolve TOC and cross-references).*

## 📖 Pedagogical Approach
The content is structured around the **Tell, Show, Do, Review** framework, incorporating progressive disclosure of complexity. Every Python concept is directly tied to the physics and mathematics of the THz spectroscopy problem being solved.
