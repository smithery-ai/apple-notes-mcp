# apple-notes-mcp MCP server

Read local Apple Notes database

## Components

### Resources

The server implements the ability to read and write to your Apple Notes.

### Prompts

The server provides multiple prompts:
- search-notes: Search notes by title or content
- list-folders: List all folders
- get-folder-notes: Get all notes in a specific folder

### Tools

Coming soon.

### Missing Features:

- No handling of encrypted notes (ZISPASSWORDPROTECTED)
- No support for pinned notes filtering
- No handling of cloud sync status
Missing attachment content retrieval
No support for checklist status (ZHASCHECKLIST)

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

Note: You might need to use the direct path to `uv`. Use `which uv` to find the path.

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
  ```json
  "mcpServers": {
    "apple-notes-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "{project_dir}",
        "run",
        "apple-notes-mcp"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  
  ```json
  "mcpServers": {
    "apple-notes-mcp": {
      "command": "uvx",
      "args": [
        "apple-notes-mcp"
      ]
    }
  }
  ```
</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory {project_dir} run apple-notes-mcp
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.