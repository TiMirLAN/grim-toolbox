from httpx import AsyncClient, TimeoutException, codes
from pydantic.dataclasses import dataclass


@dataclass
class SimpleIpInfo:
    ip: str
    asn: str
    as_name: str
    as_domain: str
    country_code: str
    country: str
    continent_code: str
    continent: str


class IpInfoClientError(Exception): ...


class IpInfoClientTimeout(Exception): ...


class IpInfoClient:
    # @TODO Move to services
    def __init__(self, token: str, timeout: float = 5.0) -> None:
        # self.client = AsyncClient(timeout=timeout)
        self.timeout = timeout
        self.params = dict(token=token)

    async def fetch_simple_data(self) -> SimpleIpInfo:
        async with AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    "https://api.ipinfo.io/lite/me", params=self.params
                )
                if response.status_code != codes.OK:
                    raise IpInfoClientError(f"Response status {response.status_code}")

                ip_data: dict[str, str] = response.json()
                return SimpleIpInfo(**ip_data)
            except TimeoutException as e:
                raise IpInfoClientTimeout(f"Timeout {self.timeout}") from e
