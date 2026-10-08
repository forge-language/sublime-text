"""Validate modern LSP registration and optional-dependency behavior without Sublime."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class PluginTest(unittest.TestCase):
    def load(self, available=True):
        lsp = types.ModuleType("LSP")
        api = types.ModuleType("LSP.plugin")
        api.registered = Mock()
        api.unregistered = Mock()

        class LspPlugin:
            def __init_subclass__(cls):
                # Documented modern API uses the package's top-level module.
                cls.name = cls.__module__.split('.')[0]

            @classmethod
            def register(cls):
                api.registered(cls)

            @classmethod
            def unregister(cls):
                api.unregistered(cls)

        api.LspPlugin = LspPlugin
        modules = {"LSP": lsp if available else None,
                   "LSP.plugin": api if available else None}
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location("LSP-Forge.plugin", ROOT / "LSP-Forge.py")
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
        return plugin, api

    def test_lifecycle_registers_once_and_unregisters_actual_plugin(self):
        plugin, api = self.load()
        plugin.plugin_unloaded()
        api.unregistered.assert_not_called()
        plugin.plugin_loaded()
        plugin.plugin_loaded()
        self.assertTrue(issubclass(plugin.ForgeLspPlugin, api.LspPlugin))
        api.registered.assert_called_once_with(plugin.ForgeLspPlugin)
        plugin.plugin_unloaded()
        plugin.plugin_unloaded()
        api.unregistered.assert_called_once_with(plugin.ForgeLspPlugin)
        plugin.plugin_loaded()
        self.assertEqual(api.registered.call_count, 2)

    def test_session_identity_and_configuration_are_inherited(self):
        plugin, api = self.load()
        self.assertEqual(plugin.ForgeLspPlugin.name, "LSP-Forge")
        # The base API manages settings resources, user command overrides and
        # process startup; this package must not replace any of those hooks.
        for override in ("configuration", "on_pre_start_async", "install_or_update",
                         "needs_update_or_installation", "register", "unregister"):
            self.assertNotIn(override, plugin.ForgeLspPlugin.__dict__)
        self.assertNotIn("register_plugin", plugin.__dict__)
        self.assertNotIn("unregister_plugin", plugin.__dict__)
        api.registered.assert_not_called()

    def test_without_lsp_import_and_unload_are_safe(self):
        plugin, api = self.load(available=False)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            plugin.plugin_loaded()
            plugin.plugin_unloaded()
        self.assertIsNone(plugin.ForgeLspPlugin)
        self.assertIn("LSP is unavailable", output.getvalue())
        self.assertNotIn("syntax", output.getvalue())
        api.registered.assert_not_called()

    def test_default_configuration_and_settings_commands(self):
        settings = json.loads((ROOT / "LSP-Forge.sublime-settings").read_text())
        self.assertEqual(settings["command"], ["forge-lsp"])
        self.assertEqual(settings["selector"], "source.forge")
        self.assertEqual(settings["initialization_options"]["forge"], settings["settings"]["forge"])
        self.assertEqual(set(settings["initialization_options"]["forge"]), {"path", "includePaths", "forgeRoot", "libDir"})
        palette = json.loads((ROOT / "Default.sublime-commands").read_text())
        self.assertEqual(palette[0]["caption"], "Preferences: LSP-Forge Settings")
        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        action = menu[0]["children"][0]["children"][0]["children"][0]
        for command in (palette[0], action):
            self.assertEqual(command["command"], "edit_settings")
            self.assertEqual(command["args"]["base_file"], "${packages}/LSP-Forge/LSP-Forge.sublime-settings")
            self.assertEqual(json.loads(command["args"]["default"])["command"], ["forge-lsp"])


if __name__ == "__main__":
    unittest.main()
