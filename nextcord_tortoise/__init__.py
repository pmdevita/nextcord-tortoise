from nextcord.ext import commands
from tortoise import Tortoise
import argparse
from typing import Optional, Union
import importlib.util

AERICH_APP = {
    "models": ["aerich.models"],
    "default_connection": "default",
}

APP_TEMPLATE = {
    "models": None,
    "default_connection": "default"
}


def attach_argparse_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("aerich")
    group.add_argument("--aerich")
    group.add_argument("--app")
    group.add_argument("--delete", action="store_true")


class ModuleNotFound(Exception):
    def __init__(self, name: str) -> None:
        msg = f'Module {name!r} could not be loaded.'
        super().__init__(msg)


class TortoiseManager:
    def __init__(self, config):
        self.config = config
        self.config["apps"] = {}
        self.config["apps"]["aerich"] = AERICH_APP.copy()

        self._has_inited = False

    def add_app(self, app_name, models):
        app = APP_TEMPLATE.copy()
        app["models"] = models
        self.config["apps"][app_name] = app

    async def on_connect(self):
        if not self._has_inited:
            self._has_inited = False
            await Tortoise.init(self.config)


class Bot(commands.Bot):
    def __init__(self, command_prefix, tortoise_config, help_command=commands.bot._default, description=None, **options):
        super().__init__(command_prefix, help_command, description, **options)
        self._tortoise = TortoiseManager(tortoise_config)
        self.add_listener(self._tortoise.on_connect, "on_connect")

    def add_cog(self, cog: commands.Cog, *, override: bool = False,
                models: Optional[Union[list[str], str]] = None) -> None:
        """Adds a "cog" to the bot and models to Tortoise.

        A cog is a class that has its own event listeners and commands.

        .. versionchanged:: 2.0

            :exc:`.ClientException` is raised when a cog with the same name
            is already loaded.

        Parameters
        -----------
        cog: :class:`.Cog`
            The cog to register to the bot.
        override: :class:`bool`
            If a previously loaded cog with the same name should be ejected
            instead of raising an error.

            .. versionadded:: 2.0
        models:
            A string or list of module loadpaths to load Tortoise ORM models
            from. Can also be a relative module path.

        Raises
        -------
        TypeError
            The cog does not inherit from :class:`.Cog`.
        CommandError
            An error happened during loading.
        .ClientException
            A cog with the same name is already loaded.
        ModuleNotFound
            A database model path could not be found.
        """

        super(Bot, self).add_cog(cog, override=override)

        cog_name = cog.__cog_name__
        cog_module = cog.__module__

        if isinstance(models, str):
            models = [models]

        # Parse the list of given models to prepare the full model path to give to Tortoise
        if models:
            module_paths = []
            for model in models:
                name = self._resolve_name(model, cog_module)

                spec = importlib.util.find_spec(name)
                if spec is None:
                    raise ModuleNotFound(name)
                module_paths.append(name)

            self._tortoise.add_app(cog_name, module_paths)


