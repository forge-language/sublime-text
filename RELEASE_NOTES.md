# LSP-Forge 0.2.0

- Migrate to Sublime LSP's `LspPlugin` API and automatic settings loading.
- Move syntax, snippets, comment settings and build commands to the independent [Forge package](https://github.com/forge-language/sublime-syntax).
- Correct the Preferences command caption.

Install **Forge** and **LSP** separately. Project LSP client keys previously named `forge` must become `LSP-Forge`; server-specific `settings.forge` and `initialization_options.forge` remain unchanged. The server is still installed manually.
