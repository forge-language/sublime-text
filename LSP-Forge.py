"""Register the manually installed Forge server with Sublime Text's LSP package."""
import sublime

SETTINGS_FILE = "LSP-Forge.sublime-settings"
SETTINGS_RESOURCE = "Packages/LSP-Forge/" + SETTINGS_FILE
_registered = False

try:
    from LSP.plugin import AbstractPlugin, register_plugin, unregister_plugin
except ImportError:
    # Syntax resources do not require LSP. Installing/enabling LSP and reloading
    # this package enables server support without downloading any executable.
    ForgeLspPlugin = None
else:
    class ForgeLspPlugin(AbstractPlugin):
        @classmethod
        def name(cls):
            return "forge"

        @classmethod
        def configuration(cls):
            # Let LSP merge user settings and expand its supported variables.
            # Preserve explicit command arrays; never infer a project command.
            return sublime.load_settings(SETTINGS_FILE), SETTINGS_RESOURCE


def plugin_loaded():
    global _registered
    if ForgeLspPlugin is None:
        print("LSP-Forge: LSP is unavailable; Forge syntax remains enabled. "
              "Install or enable LSP, then reload LSP-Forge.")
    elif not _registered:
        register_plugin(ForgeLspPlugin)
        _registered = True


def plugin_unloaded():
    global _registered
    if _registered:
        unregister_plugin(ForgeLspPlugin)
        _registered = False
