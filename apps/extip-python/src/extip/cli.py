#!/usr/bin/env python3
from pathlib import Path
from typing import Any

import click

from extip.commands.client import client
from extip.commands.service import service


@click.group()
@click.option(
    "--socket-path",
    "-s",
    default="/tmp/extip.sock",
    type=click.Path(),
    help="Path to the socket file for client connections",
    envvar="EXTIP_SOCKET",
)
@click.pass_context
def cli(ctx: dict[str, Any], socket_path: str | Path) -> None:
    ctx.ensure_object(dict)
    ctx.obj["SOCKET_PATH"] = socket_path


def main() -> None:
    cli.add_command(service)
    cli.add_command(client)
    cli()


if __name__ == "__main__":
    main()
