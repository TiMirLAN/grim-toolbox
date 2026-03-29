import asyncio
from pathlib import Path
from sys import stdout
from typing import Any

import click
from py_template_engine import TemplateEngine

from extip.service import ServiceState, Status
from extip.utils import SimpleIpInfo

DEFAULT_FORMAT = "{{info.asn}} {{info.ip}}"


async def fetch_info(socket_path: str | Path) -> ServiceState:
    (reader, *_) = await asyncio.open_unix_connection(path=socket_path)
    data = await reader.read()
    return ServiceState.model_validate_json(data)


@click.command()
@click.pass_context
@click.option(
    "--info-format",
    "-i",
    default=DEFAULT_FORMAT,
    help=f"""
    {
        ("Specify how you want to display the IP info using placeholders like:")
    } {{info.<field>}}
    The default is: "{DEFAULT_FORMAT}"
    You can use any of these fields: {", ".join(SimpleIpInfo.__annotations__.keys())}
    """,
)
def client(ctx: dict[str | Any], info_format: str) -> None:
    """Run the client to get info from socket"""
    try:
        state = asyncio.run(fetch_info(socket_path=ctx.obj["SOCKET_PATH"]))
        if state.status is Status.READY:
            stdout.write(
                TemplateEngine(template_string=info_format).render(**state.model_dump())
            )
        elif state.status is Status.UPDATING:
            stdout.write(state.message)
        elif state.status is Status.ERROR:
            stdout.write(f"Error: {state.message}")
    except FileNotFoundError:
        stdout.write("Service is not started")
    except Exception as e:
        stdout.write(f"Unknown error: {e.__class__}")
