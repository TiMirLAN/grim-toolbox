import sys
from typing import Any, Optional

import click
from loguru import logger

from extip.service import Service


@click.command()
@click.option(
    "--token",
    "-t",
    type=str,
    help="The 'ipinfo.com' access token.",
    envvar="EXTIP_TOKEN",
)
@click.option(
    "--log-level",
    "-l",
    envvar="EXTIP_LOG_LEVEL",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--log-colorize",
    "-c",
    envvar="EXTIP_LOG_COLORIZE",
    default=False,
    is_flag=True,
    help="Enable colorized output",
)
@click.option(
    "--log-format",
    "-F",
    type=str,
    envvar="EXTIP_LOG_FORMAT",
    default=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>"
        " | <level>{level: <8}</level> |"
        " <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
        " - <level>{message}</level>"
    ),
    help="""
    The log format to use. If not provided, the default format will be used.
    See the loguru documentation for more details.
    """,
)
@click.option(
    "--log-file",
    "-f",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    envvar="EXTIP_LOG_FILE",
    default=None,
    help="The file to log to. If not provided, logs will be written to stdout/stderr.",
)
@click.pass_context
def service(
    ctx: dict[str | Any],
    log_level: str,
    token: Optional[str],
    log_colorize: bool,
    log_format: Optional[str],
    log_file: Optional[str],
) -> None:
    """Start the service"""
    logger.remove()
    if log_file is None:
        # Send DEBUG, INFO, WARNING to stdout
        logger.add(
            sys.stdout,
            format=log_format,
            level=log_level,
            filter=lambda record: record["level"].name in ["DEBUG", "INFO", "WARNING"],
            colorize=log_colorize,
        )
        # Send ERROR, CRITICAL to stderr
        logger.add(
            sys.stderr,
            format=log_format,
            level="ERROR",
            filter=lambda record: record["level"].name in ["ERROR", "CRITICAL"],
            colorize=log_colorize,
        )
    else:
        logger.add(log_file, format=log_format, level=log_level)
    logger.info("Starting service...")
    Service.start(socket_path=ctx.obj["SOCKET_PATH"], token=token, logger=logger)
