import argparse
import logging
import sys
from pathlib import Path


def main() -> None:
    """Console script entry point for mcp-polarion.

    Defaults to stdio transport mode. Use --http to start in HTTP mode.
    """
    parser = argparse.ArgumentParser(
        description="Polarion MCP Server (stdio and HTTP transport)"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=False,
        help="Start in HTTP mode instead of stdio.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (HTTP mode only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (HTTP mode only).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level.",
    )
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())

    # Suppress verbose uvicorn loggers in both modes
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    if args.http:
        # --- HTTP mode ---
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )

        # Add project root to path to allow imports from lib
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from mcp_server.settings import settings  # noqa: E402
        from mcp_server.tools import mcp  # noqa: E402

        import uvicorn  # noqa: E402

        logger = logging.getLogger(__name__)

        try:
            logger.info(
                f"Successfully loaded settings for Polarion URL: {settings.polarion_url}"
            )
        except Exception as e:
            logger.critical(f"FATAL: Could not load settings. {e}")
            sys.exit(1)

        app = mcp.http_app(transport="streamable-http")

        logger.info(f"Starting Polarion MCP Server in HTTP mode on http://{args.host}:{args.port}")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
        )
    else:
        # --- Stdio mode ---
        # Configure logging to stderr BEFORE importing settings/tools
        # so that no log output leaks to stdout during module init.
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stderr,
        )

        # Add project root to path to allow imports from lib
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from mcp_server.settings import settings  # noqa: E402
        from mcp_server.tools import mcp  # noqa: E402

        # Validate required env vars by accessing settings
        try:
            _ = settings.polarion_url
        except Exception as e:
            print(
                f"Error: Missing required environment variables.\n{e}",
                file=sys.stderr,
            )
            sys.exit(1)

        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
