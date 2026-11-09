from pythonforandroid.recipe import MesonRecipe


class AubioLedfxRecipe(MesonRecipe):
    
    meson_version = "1.9.1"

    def get_recipe_env(self, arch, **kwargs):
        import os

        env = super().get_recipe_env(arch, **kwargs)
        venv = os.environ.get("VIRTUAL_ENV")

        if venv:
            site_packages = os.path.join(
                venv, "lib", "python3.12", "site-packages"
            )
            env["PYTHONPATH"] = (
                site_packages + os.pathsep + env.get("PYTHONPATH", "")
            )

        return env

    extra_build_args = ["--no-isolation"]

    version = "v0.4.11"
    url = "https://github.com/ledfx/aubio-ledfx/archive/{version}.zip"
    depends = ["numpy"]


recipe = AubioLedfxRecipe()
