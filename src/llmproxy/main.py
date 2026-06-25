"""Main entry point for llmproxy."""

import argparse
import logging
import sys
from uvicorn import run

from .config import reload_config, get_config
from .app import create_app


def parse_args():
    parser = argparse.ArgumentParser(description="llmproxy")
    parser.add_argument("-c", "--config", type=str, default=None,
                        help="Path to configuration file")
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--log-level", type=str, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    logger = logging.getLogger(__name__)

    # Load config first (this is the key)
    if args.config:
        reload_config(args.config)

    # Now create the app (it will see the correct config)
    app = create_app()

    config = get_config()

    # Apply CLI overrides
    if args.host:  config.server.host = args.host
    if args.port:  config.server.port = args.port
    if args.log_level: config.server.log_level = args.log_level

    logger.info("Starting llmproxy on %s:%s", config.server.host, config.server.port)

    try:
        run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
