#!/usr/bin/env python3
"""Run archive/syntax/plugin/LSP checks in a disposable portable Sublime profile.

Requires a pre-provisioned official Linux Sublime distribution and Xvfb. No
application download or global profile is changed. --install-lsp explicitly
permits Package Control to install its LSP dependency into the temporary profile.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
def require(condition, message):
    if not condition:
        raise AssertionError(message)

import importlib
import json
import os
import re
import sys
import traceback
import sublime
import sublime_plugin
RESULT = os.environ['FORGE_SUBLIME_RESULT']
REQUIRE = os.environ.get('FORGE_SUBLIME_REQUIRE_LSP') == '1'
INSTALL = os.environ.get('FORGE_SUBLIME_INSTALL_LSP') == '1'
state = {'build': sublime.version(), 'python_optimization': sys.flags.optimize, 'errors': [], 'syntax_assertions': 0}
view = None
attempt = 0

def finish(error=None):
    if error:
        state['errors'].append(str(error))
    with open(RESULT, 'w') as stream:
        json.dump(state, stream, indent=2)

def check_syntax():
    global view
    try:
        syntax = next((item for item in sublime.find_syntax_by_scope('source.forge') if item.path == 'Packages/LSP-Forge/Forge.sublime-syntax'), None)
        require(syntax and syntax.scope == 'source.forge', 'Archive syntax unavailable')
        fixture = os.environ['FORGE_SUBLIME_FIXTURE']
        text = open(fixture).read()
        view = sublime.active_window().new_file()
        view.run_command('append', {'characters': text})
        view.assign_syntax(syntax)
        source_row = None
        for row, line in enumerate(text.splitlines()):
            assertion = re.match('//\\s*(<-|\\^+)\\s+(.+)$', line)
            if not assertion:
                source_row = row
                continue
            marker, selector = assertion.groups()
            column = 0 if marker == '<-' else line.index('^')
            for offset in range(1 if marker == '<-' else len(marker)):
                point = view.text_point(source_row, column + offset)
                require(view.match_selector(point, selector), 'Fixture line {} column {}: {} does not match {}'.format(source_row + 1, column + offset + 1, view.scope_name(point), selector))
                state['syntax_assertions'] += 1
        require(state['syntax_assertions'], 'No syntax assertions executed')
        require(sublime.find_syntax_for_file('example.fg').scope == 'source.forge', 'Extension detection failed')
        state['archive_syntax'] = True
        editor = sublime.active_window().new_file()
        editor.assign_syntax(syntax)
        require(editor.settings().get('tab_size') == 2, 'Forge indentation setting missing')
        editor.run_command('append', {'characters': 'native main {\nprintln("{");\n// {\nreturn 0;\n}\n'})
        editor.run_command('reindent', {'single_line': False})
        formatted = editor.substr(sublime.Region(0, editor.size())).splitlines()
        require(formatted == ['native main {', '  println("{");', '  // {', '  return 0;', '}'], 'Actual indentation rules failed: ' + repr(formatted))
        editor.sel().clear()
        editor.sel().add(sublime.Region(0, 0))
        editor.run_command('toggle_comment', {'block': False})
        require(editor.substr(sublime.Region(0, editor.size())).startswith('// '), 'Comment toggle missing')
        editor.run_command('toggle_comment', {'block': False})
        require(editor.substr(sublime.Region(0, editor.size())).startswith('native main'), 'Comment untoggle failed')
        state['editor_indentation_and_comments'] = True
        sublime.set_timeout_async(start_lsp, 1000)
    except Exception:
        finish(traceback.format_exc())

def start_lsp():
    try:
        if INSTALL:
            PackageManager = importlib.import_module('Package Control.package_control.package_manager').PackageManager
            require(PackageManager().install_package('LSP'), 'Package Control LSP installation failed')
            state['lsp_provisioned'] = True
            state['installed_packages'] = os.listdir(sublime.installed_packages_path())
            finish()
            return
        sublime.set_timeout_async(check_plugin, 5000)
    except Exception:
        finish(traceback.format_exc())

def check_plugin():
    global attempt
    try:
        plugin = importlib.import_module('LSP-Forge.LSP-Forge')
        require(hasattr(plugin, 'plugin_loaded') and hasattr(plugin, 'plugin_unloaded'), 'Archive plugin missing')
        state['archive_plugin_loaded'] = True
        if plugin.ForgeLspPlugin is None:
            if REQUIRE:
                importlib.import_module('LSP.plugin')
                raise AssertionError('Real LSP dependency unavailable; install it with --install-lsp or --profile-packages')
            state['lsp'] = 'not installed; syntax-only path verified'
            finish()
            return
        require(plugin._registered, 'Helper failed to register with real LSP')
        state['lsp_plugin_registered'] = True
        source = os.environ['FORGE_SUBLIME_SOURCE']
        sublime.set_timeout(lambda: open_source(source), 0)
    except Exception:
        finish(traceback.format_exc())

def open_source(source):
    global view
    view = sublime.active_window().open_file(source)
    sublime.set_timeout_async(check_session, 1000)

def check_session():
    global attempt
    try:
        from LSP.plugin.core.registry import windows
        from LSP.plugin.core.protocol import Request
        manager = windows.lookup(view.window())
        session = manager.get_session('forge', view.file_name()) if manager else None
        if not session:
            attempt += 1
            if attempt >= 30:
                raise AssertionError('Real Sublime LSP session did not initialize in 30 seconds')
            sublime.set_timeout_async(check_session, 1000)
            return
        state['sublime_lsp_initialize'] = True
        params = {'textDocument': {'uri': 'file://' + view.file_name()}, 'position': {'line': 1, 'character': 4}}
        session.send_request_async(Request('textDocument/completion', params, view=view), completion, lambda error: finish('LSP completion failed: ' + str(error)))
    except Exception:
        finish(traceback.format_exc())

def completion(result):
    try:
        items = result if isinstance(result, list) else result['items']
        require(any((item['label'] == 'return' for item in items)), 'Forge completion absent')
        state['sublime_lsp_completion'] = True
        finish()
    except Exception:
        finish(traceback.format_exc())

def plugin_loaded():
    sublime.set_timeout(check_syntax, 3000)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sublime', type=Path, required=True, help='Official Linux sublime_text executable')
    parser.add_argument('--archive', type=Path, default=ROOT / 'dist/LSP-Forge.sublime-package')
    parser.add_argument('--lsp-command-json', default='["forge-lsp"]', help='Server argv for temporary user settings')
    parser.add_argument('--profile-packages', type=Path, help='Existing isolated Data directory containing LSP and its libraries; copied, never modified')
    parser.add_argument('--package-control', type=Path, help='Package Control archive to install into the disposable profile')
    parser.add_argument('--install-lsp', action='store_true', help='Allow Package Control network installation of LSP into disposable profile')
    parser.add_argument('--require-lsp', action='store_true', help='Fail unless real Sublime LSP initialization/completion succeeds')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--result', type=Path, help='Write JSON evidence after deleting the temporary profile')
    parser.add_argument('--save-profile', type=Path, help='Explicitly preserve this disposable profile for offline integration tests')
    args = parser.parse_args()
    executable = args.sublime.resolve()
    if not executable.is_file() or not args.archive.is_file():
        parser.error('Sublime executable and built archive must exist')
    if args.install_lsp and not args.package_control:
        parser.error('--install-lsp requires --package-control')
    command = json.loads(args.lsp_command_json)
    if not isinstance(command, list) or not command or any(not isinstance(value, str) for value in command):
        parser.error('LSP command must be a JSON argv array')
    with tempfile.TemporaryDirectory(prefix='forge-sublime-smoke-') as temporary:
        root = Path(temporary)
        distribution = root / 'sublime'
        shutil.copytree(executable.parent, distribution, ignore=shutil.ignore_patterns('Data'))
        data = distribution / 'Data'
        if args.profile_packages:
            shutil.copytree(args.profile_packages, data)
        packages = data / 'Packages'
        installed = data / 'Installed Packages'
        installed.mkdir(parents=True, exist_ok=True)
        user = packages / 'User'
        user.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.archive, installed / 'LSP-Forge.sublime-package')
        if args.package_control:
            shutil.copy2(args.package_control, installed / 'Package Control.sublime-package')
        (user / 'Preferences.sublime-settings').write_text(json.dumps({'hot_exit': False, 'remember_open_files': False, 'ignored_packages': ['Vintage']}))
        (user / 'LSP-Forge.sublime-settings').write_text(json.dumps({'enabled': True, 'command': command}))
        harness = packages / 'ForgeIntegrationTests'
        harness.mkdir(parents=True)
        (harness / '.python-version').write_text('3.8')
        (harness / 'integration.py').write_text(HARNESS)
        fixture = harness / 'syntax_test_forge.fg'
        shutil.copy2(ROOT / 'tests/syntax_test_forge.fg', fixture)
        source = root / 'main.fg'
        source.write_text('native main {\n    println("hello");\n}\n')
        result = root / 'result.json'
        env = dict(os.environ, FORGE_SUBLIME_RESULT=str(result), FORGE_SUBLIME_FIXTURE=str(fixture),
            FORGE_SUBLIME_SOURCE=str(source), FORGE_SUBLIME_REQUIRE_LSP='1' if args.require_lsp else '0',
            FORGE_SUBLIME_INSTALL_LSP='1' if args.install_lsp else '0')
        log = root / 'sublime.log'
        # Package Control libraries require a new plugin host after installation.
        # Keep the same disposable profile and restart once before exercising LSP.
        for phase in range(2 if args.install_lsp else 1):
            if phase:
                result.unlink()
                env['FORGE_SUBLIME_INSTALL_LSP'] = '0'
            with log.open('a') as output:
                process = subprocess.Popen(['xvfb-run', '-a', str(distribution / executable.name), '--multiinstance', '-n'], env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    deadline = time.monotonic() + args.timeout
                    while not result.exists() and time.monotonic() < deadline:
                        if process.poll() is not None:
                            break
                        time.sleep(.2)
                    if not result.exists():
                        raise RuntimeError('Sublime smoke timed out or exited:\n' + log.read_text()[-16000:])
                    evidence = json.loads(result.read_text())
                    if args.result:
                        args.result.write_text(json.dumps(evidence, indent=2) + '\n')
                    print(json.dumps(evidence, indent=2))
                    if args.save_profile:
                        shutil.copytree(data, args.save_profile, dirs_exist_ok=True)
                        args.save_profile.chmod(0o700)
                    if evidence['errors']:
                        raise RuntimeError('Real-editor check failed:\n' + log.read_text()[-16000:])
                finally:
                    import signal
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()



if __name__ == '__main__':
    main()
