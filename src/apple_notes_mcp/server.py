import logging
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .notes_database import NotesDatabase
import zlib
from .proto.notestore_pb2 import NoteStoreProto

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apple-notes-mcp")

notes_db = None

server = Server("apple-notes-mcp")


def decode_note_content(content: bytes | None) -> str:
    """
    Decode note content from Apple Notes binary format using protobuf decoder.
    Uses schema from: https://github.com/HamburgChimps/apple-notes-liberator
    """
    if not content:
        return "Note has no content"

    try:
        # First decompress gzip
        if content.startswith(b"\x1f\x8b"):
            decompressed = zlib.decompress(content, 16 + zlib.MAX_WBITS)

            note_store = NoteStoreProto()
            note_store.ParseFromString(decompressed)

            # Extract note text and formatting
            if note_store.document and note_store.document.note:
                note = note_store.document.note

                # Start with the basic text
                output = [note.note_text]

                # Add formatting information if available
                # Might not need this for LLM needs
                if note.attribute_run:
                    output.append("\nFormatting:")
                    for run in note.attribute_run:
                        fmt = []
                        if run.font_weight:
                            fmt.append(f"weight: {run.font_weight}")
                        if run.underlined:
                            fmt.append("underlined")
                        if run.strikethrough:
                            fmt.append("strikethrough")
                        if run.paragraph_style and run.paragraph_style.style_type != -1:
                            fmt.append(f"style: {run.paragraph_style.style_type}")
                        if fmt:
                            output.append(f"- length {run.length}: {', '.join(fmt)}")

                return "\n".join(output)
            return "No note content found"

    except Exception as e:
        return f"Error processing note content: {str(e)}"


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List all notes as resources"""
    all_notes = notes_db.get_all_notes()
    return [
        types.Resource(
            uri=f"notes://local/{note['pk']}",  # Using primary key in URI
            name=note["title"],
            description=f"Note in {note['folder']} - Last modified: {note['modifiedAt']}",
            metadata={
                "folder": note["folder"],
                "modified": note["modifiedAt"],
                "locked": note["locked"],
                "pinned": note["pinned"],
                "hasChecklist": note["checklist"],
            },
            mimeType="text/plain",
        )
        for note in all_notes
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific note's content
    Mostly from reading https://ciofecaforensics.com/2020/09/18/apple-notes-revisited-protobuf/
    and I found a gist https://gist.github.com/paultopia/b8a0400cd8406ff85969b722d3a2ebd8
    """
    if not str(uri).startswith("notes://"):
        raise ValueError(f"Unsupported URI scheme: {uri}")

    try:
        note_id = str(uri).split("/")[-1]
        note = notes_db.get_note_content(note_id)

        if not note:
            raise ValueError(f"Note not found: {note_id}")

        # Format metadata and content as text
        output = []
        output.append(f"Title: {note['title']}")
        output.append(f"Folder: {note['folder']}")
        output.append(f"Modified: {note['modifiedAt']}")
        output.append("")  # Empty line between metadata and content

        decoded = decode_note_content(note["content"])
        if isinstance(decoded, dict):
            # Here we could convert formatting to markdown or other rich text format
            # For now just return the plain text
            output.append(decoded["text"])
        else:
            output.append(decoded)

        return "\n".join(output)

    except Exception as e:
        raise RuntimeError(f"Notes database error: {str(e)}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="find-note",
            description="Find notes matching specific criteria",
            arguments=[
                types.PromptArgument(
                    name="query",
                    description="What kind of note are you looking for?",
                    required=True,
                ),
                types.PromptArgument(
                    name="folder",
                    description="Specific folder to search in",
                    required=False,
                ),
            ],
        )
    ]


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-all-notes",
            description="Get all notes",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="read-note",
            description="Get full content of a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "ID of the note to read",
                    },
                },
                "required": ["note_id"],
            },
        ),
        types.Tool(
            name="search-notes",
            description="Search through notes",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """

    if name == "search-notes":
        query = arguments.get("query")
        results = notes_db.search_notes(query)
        return [
            types.TextContent(
                type="text",
                text=f"Found {len(results)} notes:\n"
                + "\n".join(f"- {note['title']}" for note in results),
            )
        ]

    elif name == "get-all-notes":
        notes = notes_db.get_all_notes()
        return [
            types.TextContent(
                type="text",
                text="All notes:\n" + "\n".join(f"- {note['title']}" for note in notes),
            )
        ]

    elif name == "read-note":
        note_id = arguments.get("note_id")
        note = notes_db.get_note_content(note_id)
        if note:
            return [
                types.TextContent(
                    type="text",
                    text=f"Title: {note['title']}\n"
                    f"Modified: {note['modifiedAt']}\n"
                    f"Folder: {note['folder']}\n"
                    f"\nContent:\n{note['content']}",
                )
            ]
        return [types.TextContent(type="text", text="Note not found")]

    else:
        raise ValueError(f"Unknown tool: {name}")

    # Notify clients that resources have changed
    # do this when we start handling updates to notes
    await server.request_context.session.send_resource_list_changed()


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """Generate a prompt for finding notes"""
    if name != "find-note":
        raise ValueError(f"Unknown prompt: {name}")

    query = arguments.get("query", "")

    results = notes_db.search_notes(query)

    notes_context = "\n".join(
        f"- {note['title']}: {note['snippet']}" for note in results
    )

    return types.GetPromptResult(
        description=f"Found {len(results)} notes matching '{query}'",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Here are the notes that match your query:\n\n{notes_context}\n\n"
                    f"Which note would you like to read?",
                ),
            )
        ],
        resources=[
            types.Resource(
                uri=f"notes://local/{note['pk']}",
                name=note["title"],
                description=note["snippet"],
                metadata={"folder": note["folder"], "modified": note["modifiedAt"]},
            )
            for note in results
        ],
    )


async def main(db_path: str):
    # Run the server using stdin/stdout streams

    logger.info(f"Starting MCP server with db_path: {db_path}")

    global notes_db
    notes_db = NotesDatabase(db_path)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="apple-notes-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
