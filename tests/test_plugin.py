"""Validate the public LSP lifecycle and syntax-only fallback without Sublime."""
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
    def load(self, available=True, settings=None):
        sublime = types.ModuleType("sublime")
        sublime.load_settings = Mock(return_value=settings if settings is not None else {})
        lsp = types.ModuleType("LSP")
        api = types.ModuleType("LSP.plugin")
        api.AbstractPlugin = type("AbstractPlugin", (), {})
        api.register_plugin = Mock()
        api.unregister_plugin = Mock()
        modules = {"sublime": sublime, "LSP": lsp if available else None,
                   "LSP.plugin": api if available else None}
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location("forge_plugin", ROOT / "LSP-Forge.py")
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
        return plugin, sublime, api

    def test_lifecycle_registers_once_and_unregisters_actual_plugin(self):
        plugin, sublime, api = self.load()
        plugin.plugin_unloaded()
        api.unregister_plugin.assert_not_called()
        plugin.plugin_loaded()
        plugin.plugin_loaded()
        self.assertTrue(issubclass(plugin.ForgeLspPlugin, api.AbstractPlugin))
        api.register_plugin.assert_called_once_with(plugin.ForgeLspPlugin)
        plugin.plugin_unloaded()
        plugin.plugin_unloaded()
        api.unregister_plugin.assert_called_once_with(plugin.ForgeLspPlugin)
        plugin.plugin_loaded()
        self.assertEqual(api.register_plugin.call_count, 2)

    def test_configuration_preserves_user_command_and_both_protocol_objects(self):
        values = {"command": ["node", "/manually-installed/server.js", "--stdio"],
                  "initialization_options": {"forge": {"path": "/opt/forge", "includePaths": ["/opt/modules"]}},
                  "settings": {"forge": {"path": "/opt/forge", "includePaths": ["/opt/modules"]}}}
        plugin, sublime, api = self.load(settings=values)
        returned, resource = plugin.ForgeLspPlugin.configuration()
        self.assertIs(returned, values)
        self.assertEqual(resource, "Packages/LSP-Forge/LSP-Forge.sublime-settings")
        sublime.load_settings.assert_called_once_with("LSP-Forge.sublime-settings")
        self.assertEqual(plugin.ForgeLspPlugin.name(), "forge")
        api.register_plugin.assert_not_called()

    def test_without_lsp_import_and_unload_are_safe(self):
        plugin, sublime, api = self.load(available=False)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            plugin.plugin_loaded()
            plugin.plugin_unloaded()
        self.assertIsNone(plugin.ForgeLspPlugin)
        self.assertIn("syntax remains enabled", output.getvalue())
        api.register_plugin.assert_not_called()
        sublime.load_settings.assert_not_called()

    def test_default_configuration_and_settings_commands(self):
        settings = json.loads((ROOT / "LSP-Forge.sublime-settings").read_text())
        self.assertEqual(settings["command"], ["forge-lsp"])
        self.assertEqual(settings["selector"], "source.forge")
        self.assertEqual(settings["initialization_options"]["forge"], settings["settings"]["forge"])
        self.assertEqual(set(settings["initialization_options"]["forge"]), {"path", "includePaths", "forgeRoot", "libDir"})
        palette = json.loads((ROOT / "Default.sublime-commands").read_text())
        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        action = menu[0]["children"][0]["children"][0]["children"][0]
        for command in (palette[0], action):
            self.assertEqual(command["command"], "edit_settings")
            self.assertEqual(command["args"]["base_file"], "${packages}/LSP-Forge/LSP-Forge.sublime-settings")
            self.assertEqual(json.loads(command["args"]["default"])["command"], ["forge-lsp"])


if __name__ == "__main__":
    unittest.main()
