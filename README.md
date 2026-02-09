# preprint

> [!CAUTION]
> **Python 3 Only:** This project is now exclusively compatible with **Python 3.10+**. Python 2.x is no longer supported.

> [!NOTE]
> **Community Fork** - This is a fork of the original [jonathansick/preprint](https://github.com/jonathansick/preprint) package, which appears to have been discontinued in 2015. Thank you jonathansick for the original work!

## Tools for preparing scientific manuscripts in LaTeX.

Preprint lets you automatically compile, typeset document differences, and package the manuscript for publication.

### Installation

Preprint requires:

*   [`cliff`](https://cliff.readthedocs.io/en/latest/)
*   [`watchdog`](https://pypi.org/project/watchdog/)
*   [`GitPython`](https://pypi.org/project/GitPython/)
*   [`TexSoup`](https://pypi.org/project/TexSoup/)
*   A recent version of `setuptools`.

Preprint also works well with:

*   [`latexmk`](http://users.phys.psu.edu/~collins/software/latexmk-jcc/) for compiling LaTeX.
*   [`vc`](http://www.ctan.org/pkg/vc) for adding version control metadata to compiled documents.

**To install from PyPI:**

```bash
pip install preprint
```

**To install from source:**

First, clone the repository:

```bash
git clone https://github.com/dotTHzTAG/preprint.git
cd preprint
```

Then, create a virtual environment and install it in editable mode:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

After installing, try `preprint --help` for more info.

Preprint currently supports the following commands (see below for a reference):

*   `preprint make`: Performs a one-off compilation of the paper.
*   `preprint watch`: Automatically compiles the paper if the source is changed.
*   `preprint diff`: Runs `latexdiff` against a commit in Git.
*   `preprint pack`: Packages the document for journals or the arXiv.
*   `preprint init`: Sets up your project with `preprint.json` configurations.

Check the `GitHub Issues <https://github.com/dotTHzTAG/preprint/issues>` to submit additional ideas.


## A taste of preprint

Preprint is pretty easy to use.
Here are a few commands to give a flavour of what it can do:

```bash
preprint init  # this is all the setup you need
preprint make  # compiles the doc according to your compile command
preprint watch --diff 8a42f2b  # live-updating latex diff against git history
preprint pack my_paper --style arxiv  # pack it up for arXiv submission
```


## Configuration System / preprint.json


``preprint`` configurations are determined from (in order of increasing precedence): internal defaults, a project-specific JSON file, and command line arguments.

To create a ``preprint.json`` configuration file for your project, from your paper's directory, simply run:

```bash
preprint init
```

It will automatically find the root LaTeX file for your paper.
You can open ``preprint.json`` to review its format and further modify the configurations.
Here is an example of its format:

```json
{
    "cmd": "latexmk -f -pdf -bibtex-cond {master}",
    "exts": [
        "tex",
        "pdf",
        "eps",
        "png"
    ],
    "master": "article.tex"
}
```

If set in ``preprint.json``, any command-line setting of the same name does not need to be repeated.

## List of Configurations


master

  * (type: string) Name of the LaTeX document to be compiled (or the root LaTeX document containing `\documentclass`).
  * Defaults to ``'article.tex'``, but ``preprint init`` will set this for you.

exts

  * (type: list of strings) List of file extensions used by the ``watch`` command.
  * If any file with this extension is changed in the project, ``preprint watch``will trigger a compile.
  * This setting is also used by ``preprint pack`` to figure out your preferences for figure file types.
  * For example, ``["tex", "pdf", "eps", "png"]`` will try to include ``pdf`` figures before falling back to ``eps`` files, while ``["tex", "eps", "pdf", "png"]`` will have the opposite behaviour.
  * Defaults to ``["tex", "pdf", "eps", "png"]``.

cmd

  * (type: string) The command to run when making a document.
  * This is used by ``preprint make`` and ``preprint watch`` (``preprint diff`` and ``preprint watch --diff`` will always use `latexmk`).
  * The command string can include ``{master}`` to interpolate the path of the master tex file.
  Defaults to ``"latexmk -f -pdf -bibtex-cond {master}"``.


## Command Reference


### init


``preprint init`` will create a default ``preprint.json`` configuration file for your project.

Usage:

```bash
preprint init
```

After running, open ``preprint.json`` to edit the configuration.
See *'Configuration System / preprint.json'* (above) for more information.

### make


``preprint make`` will perform a one-off compilation of your paper.

Usage:

```bash
preprint [--master MASTER] make [--cmd CMD]
```

Optional arguments:
*   `--master`   Name of the root LaTeX file (e.g., `paper.tex`)
*   `--cmd`      Name of command to run for compilation


If `preprint.json` is set up, you can just run:

```bash
preprint make
```

> [!TIP]
> If `latexmk` reports "Nothing to do" or you encounter unexpected compilation issues, try running `latexmk -C` in your manuscript directory before `preprint make`. This thoroughly cleans all temporary LaTeX files and often resolves stubborn compilation problems.

### watch


``preprint watch`` will automatically compile your paper if a TeX or graphics source file is changed.

Usage:

```bash
preprint [--master MASTER] watch [--exts EXT1, ..., EXTN; --cmd CMD; --diff [SHA]]
```

Optional arguments:

*   `--master`   Name of the root LaTeX file (e.g., `paper.tex`)
*   `--exts`     List of file extensions (defaults to `pdf eps tex`)
*   `--cmd`      Name of command to run when a change occurs
*   `--diff`     Run a latexdiff compile against the given commit SHA from the git repository (HEAD if blank).

For example, to continuously compile the document whenever `.tex` or figures have changed, and assuming you've setup a `preprint.json` file with the name of your master document, just run:

```bash
preprint watch
```

To continuously run a latexdiff-based compile, showing all changes you've made against the HEAD of the git repository, run:

```bash
preprint watch --diff
```

The document will be saved to `build/PAPER_NAME_diff.pdf`.
This is a nice way of keeping track of what you're doing.

Finally, to continuously run a latexdiff-based compile against an arbitrary commit in your git history, just copy the commit SHA fragment (say, `b91688d`) and run:

```bash
preprint watch --diff b91688d
```

### diff


``preprint diff`` will typeset the document with revisions highlighted between the currently checked-out version and a previous git commit.

* This command is powered by the `latexdiff <http://latexdiff.berlios.de>` (which is probably installed with your TeX distribution).
* The command also requires `latexmk <http://users.phys.psu.edu/~collins/software/latexmk-jcc/>` to compile the difference document.
* This command is compatible with documents that use ``\input{}`` to combine text documents; in fact, included documents are inlined recursively.
* ``preprint diff`` was inspired by `this blog post <http://astrowizici.st/blog/2013/10/04/publishing-with-git/>` by Andy Casey.

Usage:

```bash
preprint [--master MASTER] diff PREV_SHA [-n NAME]
```

Arguments:

*   `PREV_SHA`   A SHA fragment or tag name pointing to the previous revision.

Optional arguments:

*   `--master`   Name of the root LaTeX file (e.g., `paper.tex`)
*   `-n`         Output name of the difference document (e.g., `diff.tex`)


### pack


``preprint pack`` prepares a preprint for submission to a journal.
This pipeline includes:

1.  Creating a build directory and copying over just the required manuscript files.
2.  Inlining all input LaTeX files (either with `\input{}` or `\InputIfFileExists` syntax).
3.  Copying the `.bbl` bibliography or inlining it into the manuscript, as necessary.
4.  Moving figures to the root directory and updating the tex source.
5.  Deleting comments; don't be a tweet on @OverheardOnAph.
6.  Renaming figures to conform to AASTeX if necessary.
7.  Making JPEG versions of figures to fulfil arXiv file size requirements, if necessary. This requires `imagemagick <http://www.imagemagick.org/script/index.php>`.

This command is inspired by Erik Tollerud's `Astropysics package <http://pythonhosted.org/Astropysics/coremods/publication.html>`, but is designed around regular expressions for text transformation.
The implementation should thus be easier.

Usage:

```bash
preprint [--master MASTER] pack NAME [--style STYLE; --exts EXT1, ..., EXTN]
```

Arguments:

*   `NAME`   Name of the build. Products copied to `build/NAME` directory.

Optional arguments:

*   `--master`   Name of the root LaTeX file (e.g., `paper.tex`)
*   `--exts`     File format priority for figures (e.g., `eps, pdf`)
*   `--style`    Style for the build (default is `aastex`, can also be `arxiv`).
*   `--maxsize`  Maximum size of figure in MB before compressing into jpg (for `arxiv`). Default is 2.5 MB.

Note that the ``--exts`` option can be used to prefer a certain file format for the build if you maintain both EPS and PDF figure sets.
For example, to generate a manuscript for a AAS journal, run:

```bash
preprint pack my_aas_build --style aastex --exts eps
```

And to build for the arxiv, where PDF figures are preferred, run:

```bash
preprint pack my_arxiv_build --style arxiv --exts pdf
```

### About


#### Original author:

Preprint was originally developed on GitHub <https://github.com/jonathansick/preprint>.

Contributions and suggestions are welcome.
Read the [CONTRIBUTING guidelines](https://github.com/dotTHzTAG/preprint/blob/main/CONTRIBUTING.md) for instructions on how to help.

Copyright 2014 Jonathan Sick, @jonathansick

#### Current Fork

This is a community fork to ensure the original package continues to work with Python 3. Any contributions are absolutely welcome.

Licensed BSD.
