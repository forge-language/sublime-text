"""Connect a manually installed Forge server through Sublime Text's LSP package."""
from copy import deepcopy

from LSP.plugin import LspPlugin, OnPreStartContext

_registered = False


class ForgeLspPlugin(LspPlugin):
    @classmethod
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        # Native Forge reads initialization options; TypeScript also reads
        # configuration updates. Users configure both through settings.forge.
        config = context.configuration
        config.initialization_options.set("forge", deepcopy(config.settings.get("forge", {})))


def plugin_loaded() -> None:
    global _registered
    if not _registered:
        ForgeLspPlugin.register()
        _registered = True


def plugin_unloaded() -> None:
    global _registered
    if _registered:
        ForgeLspPlugin.unregister()
        _registered = False
