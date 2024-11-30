# Default make command
all: help

## reinstall-deps: Reinstall dependencies with uv
reinstall-deps:
	uv sync --reinstall

## build: Build the package
build:
	uv build

## publish: Publish the package to PyPI
publish:
	uv publish

## release: Create and push a new release tag
release:
	@if [ -z "$$VERSION" ]; then \
		echo "Error: VERSION is required. Use 'make release VERSION=x.x.x'"; \
		exit 1; \
	fi
	@echo "Creating release v$$VERSION..."
	git tag -a v$$VERSION -m "Release v$$VERSION"
	git push origin v$$VERSION
	@echo "\nRelease v$$VERSION created!"
	@echo "Users can install with:"
	@echo "  uvx install github:yourusername/apple-notes-mcp@v$$VERSION"
	@echo "  uv pip install git+https://github.com/yourusername/apple-notes-mcp.git@v$$VERSION"

## inspect-local-server: Inspect the local MCP server
inspect-local-server:
	npx @modelcontextprotocol/inspector uv --directory . run apple-notes-mcp --db-path NoteStore.sqlite

## help: Show a list of commands
help : Makefile
	@echo "Usage:"
	@echo "  make [command]"
	@echo ""
	@echo "Commands:"
	@sed -n 's/^##//p' $< | awk 'BEGIN {FS = ": "}; {printf "\033[36m%-40s\033[0m %s\n", $$1, $$2}'


.PHONY: all help