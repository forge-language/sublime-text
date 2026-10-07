# LSP-Forge

Forge language support for Sublime Text 4 (build 4132 or newer), licensed under Apache 2.0.

The package provides `.fg` syntax highlighting, comment toggling, snippets, project build/run commands and integration with the [Forge language server](https://github.com/forge-language/language-server). Diagnostics, completion, hover and document symbols require the separately installed **LSP** package, Forge compiler and language server. Syntax highlighting works without them.

## Install

### Package Control repository

Until the package is accepted into the default channel, run **Package Control: Add Repository** and enter:

```
https://raw.githubusercontent.com/forge-language/sublime-text/main/packages.json
```

Then run **Package Control: Install Package** and select **LSP-Forge**. Install **LSP** separately for language-server features. GitHub version tags provide subsequent package updates.

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
  "initialization_options": {
    "forge": {
      "path": "/absolute/path/to/forge",
      "includePaths": ["/absolute/path/to/project/modules"]
    }
  },
  "settings": {
    "forge": {
      "path": "/absolute/path/to/forge",
      "includePaths": ["/absolute/path/to/project/modules"]
    }
  }
}
```

The native server reads `initialization_options.forge`; the TypeScript server also receives `settings.forge` configuration updates. Keep both aligned when overriding paths. Optional `forgeRoot` and `libDir` belong inside these Forge objects only when using a custom toolchain layout. The default command is `forge-lsp`; no server is downloaded or built automatically.

The separately built TypeScript server is also supported:

```json
{
  "command": ["/absolute/path/to/node", "/absolute/path/to/language-server/out/server.js", "--stdio"]
}
```

Build it with `npm ci && npm run build` in the [language-server repository](https://github.com/forge-language/language-server#typescript-server), using Node.js 18 or newer. This is an alternative to the native server, not a bundled npm dependency.

The syntax package is platform independent. Compiler/server availability depends on their supported platforms; the current public Forge SDK targets Linux x86-64 with glibc 2.35 or newer.

## Build and run

Open a Forge project folder and select **Tools > Build System > Forge**. The default build runs `forge build`; variants provide **Check File** and **Run Project**. Project commands use the Sublime project directory, first open folder, or current file directory as a fallback. For a multi-folder project, select the intended project root. Check File parses the saved file using `forge FILE --check`; it is not a substitute for building/linking the project.

Build/run actions execute only when explicitly invoked. Commands use argument arrays rather than a shell. Review package source and grant any Forge native/npm trust required by your dependencies before building or running them. The plugin does not install dependencies, grant trust or evaluate repository settings itself.

## Develop and release

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/build-package.py
python3 scripts/test-sublime.py --sublime /path/to/sublime_text/sublime_text
```

The build writes `dist/LSP-Forge.sublime-package` and its SHA-256 file from an explicit resource list with fixed archive timestamps. Development scripts, tests, credentials and caches are excluded. See `scripts/test-sublime.py` for isolated real-editor checks; the syntax fixture is `tests/syntax_test_forge.fg`.

Main/PR CI validates and builds the archive. Pushing a semantic version tag such as `v0.1.0` runs validation and publishes a GitHub Release with the package and checksum. Default-channel submission follows [Package Control's submission process](https://packages.sublimetext.com/docs/submitting_a_package).
