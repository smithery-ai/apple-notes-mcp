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