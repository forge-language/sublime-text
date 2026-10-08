"""Connect a manually installed Forge server through Sublime Text's LSP package."""
_registered = False

try:
    from LSP.plugin import LspPlugin
except ImportError:
    ForgeLspPlugin = None
else:
    class ForgeLspPlugin(LspPlugin):
        # LSP derives the session name and settings resource from LSP-Forge.
        # Server installation and command selection remain under user control.
        pass


def plugin_loaded():
    global _registered
    if ForgeLspPlugin is None:
        print("LSP-Forge: LSP is unavailable. Install, update or enable LSP, "
              "then reload LSP-Forge.")
    elif not _registered:
        ForgeLspPlugin.register()
        _registered = True


def plugin_unloaded():
    global _registered
    if _registered:
        ForgeLspPlugin.unregister()
        _registered = False
