from os.path import join
from pathlib import Path
from pythonforandroid.recipe import PyProjectRecipe


class SamplerateLedfxRecipe(PyProjectRecipe):
    extra_build_args = ["--no-isolation"]

    version = 'v0.2.3'
    url = 'git+https://github.com/ledfx/python-samplerate-ledfx'

    depends = ['numpy']

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)

        # AUTO_HOSTPY_PYTHONPATH: Use the proven p4a Python 3.11 environment.
        import os
        from pathlib import Path

        host = (
            Path(self.ctx.build_dir)
            / "other_builds"
            / "hostpython3"
            / "desktop"
            / "hostpython3"
            / "native-build"
        )

        if not (host / "python3").is_file():
            raise RuntimeError("p4a host Python 3.11 is missing")

        paths = [
            str(host / "Lib"),
            str(host / "Lib/site-packages"),
            str(host / "build/lib.linux-x86_64-3.11"),
        ]

        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])

        env["PYTHONPATH"] = os.pathsep.join(paths)

        
        python_lib = (
            Path(self.ctx.build_dir)
            / "other_builds"
            / "python3"
            / f"{arch.arch}__ndk_target_24"
            / "python3"
            / "android-build"
            / "libpython3.11.so"
        )

        if not python_lib.is_file():
            raise FileNotFoundError(f"Android Python library missing: {python_lib}")

        env['CMAKE_ARGS'] = ' '.join([
            f'-DPYTHON_LIBRARY={python_lib}',
            f'-DPYTHON_LIBRARIES={python_lib}',
            env.get('CMAKE_ARGS', ''),  # existing CMAKE_ARGS, if any
            '-DCMAKE_SYSTEM_NAME=Android',  # tell cmake to cross compile for Android
            f'-DCMAKE_ANDROID_ARCH_ABI={arch.arch}',  # set ABI version
            f'-DCMAKE_ANDROID_NDK={self.ctx.ndk_dir}',  # set NDK path
            '-DPYBIND11_USE_CROSSCOMPILING=ON',  # tell pybind11 we're cross compiling
            '-DPYBIND11_FINDPYTHON=OFF',  # disable pybind11's FindPython
            f'-DPYTHON_INCLUDE_DIRS={self.ctx.python_recipe.include_root(arch.arch)}'  # tell pybind11 where to find Python
        ])
        
        return env


recipe = SamplerateLedfxRecipe()
