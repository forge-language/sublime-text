# LSP-Forge

Forge language-server integration for Sublime Text 4 (build 4132 or newer), licensed under Apache 2.0.

This package uses Sublime LSP's `LspPlugin` API for diagnostics, completion, hover and document symbols. Install the independent [Forge syntax package](https://github.com/forge-language/sublime-syntax), **LSP**, and a Forge language server. Syntax highlighting, snippets and build commands belong to **Forge**, which works without LSP.

## Upgrade from 0.1.0

Install **Forge** before upgrading to 0.2.0; syntax and editor resources have moved out of LSP-Forge. If your project configures an LSP client under the old name `forge`, rename that client key to `LSP-Forge`. Server options keep their names inside `settings.forge`. Move any overrides from `initialization_options.forge` to `settings.forge` and remove the old initialization overrides; `settings.forge` is now authoritative. Remove any old unpacked development copy before installing the new archive.

## Install

### Package Control repository

Until the package is accepted into the default channel, run **Package Control: Add Repository** and enter:

```
https://raw.githubusercontent.com/forge-language/sublime-text/main/packages.json
```

Then run **Package Control: Install Package** and select **LSP-Forge**. Install **LSP** and the separate **Forge** syntax package as well. GitHub version tags provide subsequent package updates.

### Release file

Download `LSP-Forge.sublime-package` and its SHA-256 file from [GitHub Releases](https://github.com/forge-language/sublime-text/releases/latest). Verify the checksum and place the archive, without unzipping it, in Sublime Text's **Installed Packages** folder. Locate this folder by opening **Preferences > Browse Packages…** and navigating to the adjacent `Installed Packages` directory. Restart Sublime Text after installation.

Do not keep both an unpacked `Packages/LSP-Forge` development copy and an installed archive: the unpacked copy takes precedence. Manual installations must be updated manually; Package Control installations track release tags.

## Language server

1. Install the [Forge SDK](https://forge-lang.org) for a supported compiler platform.
2. Build/install `forge-lsp` using the [language-server native instructions](https://github.com/forge-language/language-server#native-server).
3. Install **LSP** through Package Control.
4. Put `forge-lsp` and `forge` on Sublime Text's PATH, or set absolute paths in **Preferences: LSP-Forge Settings**.

If LSP was installed after LSP-Forge, restart Sublime Text to load the integration.

Sublime Text launched from the desktop may have a different PATH than a terminal. For example:

```json
{
  "command": ["/absolute/path/to/forge-lsp"],
  "settings": {
    "forge": {
      "path": "/absolute/path/to/forge",
      "includePaths": ["/absolute/path/to/project/modules"]
    }
  }
}
```

Configure compiler options only in `settings.forge`. At startup, the plugin copies that object to the initialization options used by both servers. The TypeScript server also reads subsequent configuration updates; restart the native server after changing compiler settings. Optional `forgeRoot` and `libDir` belong in `settings.forge` when using a custom toolchain layout. The default settings file includes comments explaining each option. The default command is `forge-lsp`; no server is downloaded or built automatically.

The separately built TypeScript server is also supported:

```json
{
  "command": ["/absolute/path/to/node", "/absolute/path/to/language-server/out/server.js", "--stdio"]
}
```

Build it with `npm ci && npm run build` in the [language-server repository](https://github.com/forge-language/language-server#typescript-server), using Node.js 18 or newer. This is an alternative to the native server, not a bundled npm dependency.

The separate Forge syntax package is platform independent. Compiler/server availability depends on their supported platforms; the current public Forge SDK targets Linux x86-64 with glibc 2.35 or newer.

## Develop and release

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/build-package.py
python3 scripts/test-sublime.py --sublime /path/to/sublime_text/sublime_text \
  --syntax-archive ../sublime-syntax/dist/Forge.sublime-package \
  --fixture ../sublime-syntax/tests/syntax_test_forge.fg
```

The build writes `dist/LSP-Forge.sublime-package` and its SHA-256 file from an explicit resource list with fixed archive timestamps. Development scripts, tests, credentials and caches are excluded. See `scripts/test-sublime.py` for isolated real-editor checks; the syntax fixture is maintained in the independent syntax repository.

Main/PR CI validates and builds the archive. Pushing a semantic version tag such as `v0.2.0` runs validation and publishes a GitHub Release with the package and checksum. Default-channel submission follows [Package Control's submission process](https://packages.sublimetext.com/docs/submitting_a_package).
