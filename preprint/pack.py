import logging
import os
import shutil
import codecs
import re
import subprocess

from .texutils import inline, remove_comments, inline_bbl, _find_exts

from cliff.command import Command


class Package(Command):
    """Package manuscript for arxiv/journal submission"""

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Package, self).get_parser(prog_name)
        parser.add_argument(
            'name',
            nargs='?',  # Make name argument optional
            default=None, # Set default to None if not provided
            help="Name of packaged manuscript (saved to build/name).")
        parser.add_argument(
            '--style',
            default="aastex",
            choices=['aastex', 'arxiv'],
            help="Build style (aastex, arxiv).")
        parser.add_argument(
            '--exts',
            nargs='*',
            default=self.app.confs.config('exts') + ['png'],
            help="Figure extensions to use in order of priority")
        parser.add_argument(
            '--jpeg',
            action='store_true',
            default=False,
            help="Make JPEG versions of figures if too large (for arxiv)")
        parser.add_argument(
            '--maxsize',
            default=2.,
            type=float,
            help="Max figure size (MB) before converting to JPEG (for arxiv)")
        self.log.debug("pack: get_parser configured. Default style: %s, default exts: %s, default jpeg: %s, default maxsize: %s",
                       parser.get_default('style'), parser.get_default('exts'),
                       parser.get_default('jpeg'), parser.get_default('maxsize'))
        return parser

    def take_action(self, parsed_args):
        # Explicitly set this command's logger to DEBUG if global debug is on
        if self.app.options.debug:
            self.log.setLevel(logging.DEBUG)

        self.log.debug("pack: take_action started.")
        package_name = parsed_args.name
        master_file_path = self.app.options.master
        self.log.debug("pack: Initial package_name: %s, master_file_path: %s", package_name, master_file_path)

        if package_name is None:
            # Derive package name from master file if not provided
            package_name = os.path.splitext(os.path.basename(master_file_path))[0]
            self.log.debug("pack: Package name not provided, derived from master file: %s", package_name)
        else:
            self.log.debug("pack: Using provided package name: %s", package_name)

        dirname = os.path.join("build", package_name)
        self.log.debug("pack: Target directory for packaging: %s", dirname)
        if not os.path.exists(dirname):
            self.log.debug("pack: Creating target directory: %s", dirname)
            os.makedirs(dirname)

        self._build_style = parsed_args.style
        self._ext_priority = parsed_args.exts
        self._max_size = parsed_args.maxsize
        self.log.debug("pack: Build style: %s, Extension priority: %s, Max figure size: %s MB",
                       self._build_style, self._ext_priority, self._max_size)

        self.log.debug("pack: Master file path from options: %s", master_file_path)
        self.log.debug("pack: Current working directory for script: %s", os.getcwd())
        self.log.debug("pack: os.path.exists('%s') returns: %s", master_file_path, os.path.exists(master_file_path))

        bbl_path = os.path.splitext(master_file_path)[0] + '.bbl'
        self.log.debug("pack: Expected bbl_path from master file: %s", bbl_path)
        self.log.debug("pack: os.path.exists('%s') returns: %s", bbl_path, os.path.exists(bbl_path))

        try:
            with codecs.open(master_file_path, 'r', encoding='utf-8') as f:
                root_text = f.read()
            self.log.debug("pack: Master tex file '%s' read successfully.", master_file_path)
        except FileNotFoundError:
            self.log.error("pack: Master tex file '%s' not found. Exiting.", master_file_path)
            return
        except Exception as e:
            self.log.error("pack: An unexpected error occurred while reading master file '%s': %s", master_file_path, e)
            return

        tex = inline(root_text)
        self.log.debug("pack: LaTeX inlined.")
        tex = remove_comments(tex)
        self.log.debug("pack: Comments removed from LaTeX.")
        tex = self._process_figures(tex, dirname)
        self.log.debug("pack: Figures processed.")

        if os.path.exists(bbl_path):
            self.log.debug("pack: bbl file '%s' exists, attempting to inline.", bbl_path)
            with codecs.open(bbl_path, 'r', encoding='utf-8') as f:
                bbl_text = f.read()
            tex = inline_bbl(tex, bbl_text)
            self.log.debug("pack: bbl content inlined.")
        else:
            self.log.debug("pack: Skipping .bbl installation, file '%s' not found.", bbl_path)

        if self._build_style == "aastex":
            output_tex_path = os.path.join(dirname, "ms.tex")
            self.log.debug("pack: Using AASTex style, output tex path: %s", output_tex_path)
        else:
            output_tex_path = os.path.join(
                dirname,
                os.path.basename(master_file_path))
            self.log.debug("pack: Using non-AASTex style, output tex path: %s", output_tex_path)
        self._write_tex(tex, output_tex_path)
        self.log.debug("pack: Output tex written.")
        self.log.debug("pack: take_action completed.")

    def _process_figures(self, tex, dirname):
        self.log.debug("pack: _process_figures started. Output directory %s", dirname)
        figs = self._discover_figures(tex, self._ext_priority)
        self.log.debug("pack: Discovered figures: %s", figs)
        if self._build_style == "aastex":
            maxsize = None
            self.log.debug("pack: AASTex style, no maxsize limit for figures.")
        elif self._build_style == "arxiv":
            maxsize = self._max_size
            self.log.debug("pack: Arxiv style, maxsize limit for figures: %s MB", maxsize)

        tex = self._install_figs(
            tex, figs, dirname,
            naming=self._build_style,
            format_priority=self._ext_priority,
            max_size=maxsize)
        self.log.debug("pack: Figures installed. Tex updated.")
        return tex

    def _write_tex(self, tex, path):
        """Write the LaTeX to the output path."""
        self.log.debug("pack: _write_tex started. Output path %s", path)
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(tex)
        self.log.debug("pack: _write_tex completed.")

    def _discover_figures(self, tex, ext_priority):
        self.log.debug("pack: _discover_figures started. Extension priority: %s", ext_priority)
        figs_pattern = re.compile(r"\\includegraphics(.*?){(.*?)}", re.UNICODE)
        matches = figs_pattern.findall(tex)
        self.log.debug("pack: Found %d includegraphics matches.", len(matches))
        figs = {}
        for i, match in enumerate(matches):
            opts, path = match
            self.log.debug("pack: Match %d: opts='%s', path='%s'", i, opts, path)
            basename = os.path.splitext(os.path.basename(path))[0]
            # Find all formats this file exists in
            exts = _find_exts(path, ext_priority) # Still using global _find_exts
            self.log.debug("pack: Found extensions for %s: %s", path, exts)
            # Get file sizes for all variants here
            _dir = os.path.dirname(path)
            sizes = []
            for ext in exts:
                p = os.path.join(_dir, ".".join((basename, ext)))
                if os.path.exists(p):
                    sizes.append(os.path.getsize(p) / 10. ** 6.)
                else:
                    sizes.append(0.0) # Indicate not found
            figs[basename] = {"path": path,
                              "exts": exts,
                              "size_mb": sizes,
                              "options": opts,
                              "env": r"\\includegraphics",
                              "num": i + 1}
            self.log.debug("pack: Figure %s details: %s", basename, figs[basename])
        return figs

    def _install_figs(self, tex, figs, install_dir, naming=None,
                     format_priority=('pdf', 'eps', 'ps', 'png', 'jpg', 'tif'),
                     max_size=None):
        self.log.debug("pack: _install_figs started. Install directory: %s, Naming: %s, Max size: %s", install_dir, naming, max_size)
        for figname, fig in figs.items():
            self.log.debug("pack: Processing figure %s: %s", figname, fig)
            if len(fig['exts']) == 0:
                self.log.debug("pack: No extensions found for figure %s, skipping.", figname)
                continue
            # get the priority graphics file type
            full_path = None
            selected_ext = None
            for ext in format_priority:
                if ext in fig['exts']:
                    figsize = fig['size_mb'][fig['exts'].index(ext)]
                    full_path = os.path.join(os.path.dirname(fig['path']), ".".join((os.path.splitext(os.path.basename(fig['path']))[0], ext)))
                    selected_ext = ext
                    self.log.debug("pack: Selected full_path for %s: %s (size %f MB, ext: %s)", figname, full_path, figsize, selected_ext)
                    break
            if full_path is None:
                self.log.warning("pack: Could not determine full_path for figure %s based on format_priority %s, skipping.", figname, format_priority)
                continue

            # copy fig to the build directory
            if naming == "aastex":
                install_path = os.path.join(
                    install_dir,
                    f"f{fig['num']:d}.{selected_ext}")
                self.log.debug("pack: AASTex naming convention, install_path: %s", install_path)
            elif naming == "arxiv":
                install_path = os.path.join(
                    install_dir,
                    f"figure{fig['num']:d}.{selected_ext}")
                self.log.debug("pack: Arxiv naming convention, install_path: %s", install_path)
            else:
                install_path = os.path.join(
                    install_dir,
                    os.path.basename(full_path))
                self.log.debug("pack: Default naming convention, install_path: %s", install_path)
            self.log.debug("pack: Copying %s to %s", full_path, install_path)
            figs[figname]["installed_path"] = install_path
            self.log.debug("pack: Copying source %s to destination %s", full_path, install_path)
            try:
                shutil.copy(full_path, install_path)
                self.log.debug("pack: Successfully copied %s to %s", full_path, install_path)
            except FileNotFoundError:
                self.log.error("pack: Source figure %s not found for copying, skipping.", full_path)
                continue
            if max_size and figsize > max_size:
                self.log.debug("pack: Figure %s size %f MB exceeds max size %f MB, attempting to rasterize.", figname, figsize, max_size)
                self._rasterize_figure(install_path)
            # update tex by replacing old filename with new.
            # Note that fig['env'] currently has escaped slash for re; this is
            # removed here. Might want to think of a convention so it's less kludgy
            old_fig_cmd = r"{env}{opts}{{{path}}}".format(
                env=fig['env'].replace("\\\\", "\\"),
                opts=fig['options'],
                path=fig['path'])
            new_fig_cmd = r"{env}{opts}{{{path}}}".format(
                env=fig['env'].replace("\\\\", "\\"),
                opts=fig['options'],
                path=os.path.basename(os.path.splitext(install_path)[0])) # Use basename without extension for tex
            self.log.debug("pack: Replacing '%s' with '%s' in tex content.", old_fig_cmd, new_fig_cmd)
            tex = tex.replace(old_fig_cmd, new_fig_cmd)
        return tex

    def _rasterize_figure(self, original_path):
        """Make a JPEG version of a figure, deleting the original."""
        self.log.debug("pack: _rasterize_figure started for %s", original_path)
        jpg_path = os.path.splitext(original_path)[0] + ".jpg"
        convert_cmd = "convert -density 300 -trim -quality 80 {path} {jpgpath}".format(
                path=original_path, jpg_path=jpg_path)
        self.log.debug("pack: Executing rasterize command: %s", convert_cmd)
        return_code = subprocess.call(convert_cmd, shell=True)
        if return_code != 0:
            self.log.error("pack: Rasterize command failed with return code %d for %s", return_code, original_path)
        else:
            self.log.debug("pack: Rasterize command successful for %s", original_path)
            os.remove(original_path)
            self.log.debug("pack: Rasterized %s to %s and removed original.", original_path, jpg_path)
