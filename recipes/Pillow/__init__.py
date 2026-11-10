from os.path import join

from pythonforandroid.recipe import PyProjectRecipe


class PillowRecipe(PyProjectRecipe):
    extra_build_args = ["--no-isolation"]
    """
    A recipe for Pillow (previously known as Pil).

    This recipe allow us to build the Pillow recipe with support for different
    types of images and fonts. But you should be aware, that in order to  use
    some of the features of  Pillow, we must build some libraries. By default
    we automatically trigger the build of below libraries::

        - freetype: rendering fonts support.
        - harfbuzz: a text shaping library.
        - jpeg: reading and writing JPEG image files.
        - png: support for PNG images.

    But you also could enable the build of some extra image types by requesting
    the build of some libraries via argument `requirements`::

        - libwebp: library to encode and decode images in WebP format.
    """

    version = '11.3.0'
    url = 'https://github.com/python-pillow/Pillow/archive/{version}.tar.gz'
    site_packages_name = 'PIL'
    patches = ["setup.py.patch"]
    depends = ['png', 'jpeg', 'freetype']
    hostpython_prerequisites = ["setuptools==84.2.1"]
    opt_depends = ['libwebp']

    def install_hostpython_prerequisites(self, packages=None, force_upgrade=True):
        super().install_hostpython_prerequisites(packages, force_upgrade)

        from pathlib import Path

        site = Path(self.hostpython_site_dir)
        stale = site / "setuptools-69.2.0-py3.11.egg-info"
        current = site / "setuptools-84.2.1.dist-info"

        if stale.exists():
            if not current.is_dir():
                raise RuntimeError("Required setuptools 84.2.1 metadata missing")

            backup = site.parent / "setuptools-metadata-backup"
            destination = backup / stale.name

            if destination.exists():
                print("WARNING: Obsolete setuptools metadata returned")

            number = 1
            while destination.exists():
                destination = backup / f"{stale.name}.repeat-{number}"
                number += 1

            backup.mkdir(exist_ok=True)
            stale.rename(destination)
            print("PASS: Obsolete setuptools metadata quarantined")

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)

        jpeg = self.get_recipe('jpeg', self.ctx)
        jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)
        env["JPEG_ROOT"] = "{}:{}".format(jpeg_lib_dir, jpeg_inc_dir)

        freetype = self.get_recipe('freetype', self.ctx)
        free_lib_dir = join(freetype.get_build_dir(arch.arch), 'objs', '.libs')
        free_inc_dir = join(freetype.get_build_dir(arch.arch), 'include')
        env["FREETYPE_ROOT"] = "{}:{}".format(free_lib_dir, free_inc_dir)

        # harfbuzz is a direct dependency of freetype and we need the proper
        # flags to successfully build the Pillow recipe, so we add them here.
        harfbuzz = self.get_recipe('harfbuzz', self.ctx)
        harf_lib_dir = join(harfbuzz.get_build_dir(arch.arch), 'src', '.libs')
        harf_inc_dir = harfbuzz.get_build_dir(arch.arch)
        env["HARFBUZZ_ROOT"] = "{}:{}".format(harf_lib_dir, harf_inc_dir)

        env["ZLIB_ROOT"] = f"{arch.ndk_lib_dir_versioned}:{self.ctx.ndk.sysroot_include_dir}"

        # libwebp is an optional dependency, so we add the
        # flags if we have it in our `ctx.recipe_build_order`
        if 'libwebp' in self.ctx.recipe_build_order:
            webp = self.get_recipe('libwebp', self.ctx)
            webp_install = join(
                webp.get_build_dir(arch.arch), 'installation'
            )
            env["WEBP_ROOT"] = f"{join(webp_install, 'lib')}:{join(webp_install, 'include')}"
        return env


recipe = PillowRecipe()
