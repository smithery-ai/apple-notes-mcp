from . import server
import asyncio
import argparse


def main():
    parser = argparse.ArgumentParser(description="Apple Notes MCP Server")
    parser.add_argument(
        "--db-path",
        default="",
        help="Path to Apple Notes database file. Will use OS default if not provided.",
    )
    args = parser.parse_args()
    asyncio.run(server.main(args.db_path))


# Optionally expose other important items at package level
__all__ = ["main", "server"]
