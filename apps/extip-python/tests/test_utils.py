from types import TracebackType

import pytest

pytest.importorskip("httpx")
import httpx

from extip.utils import (
    IpInfoClient,
    IpInfoClientError,
    IpInfoClientTimeout,
    SimpleIpInfo,
)


def test_simple_ip_info_initialization() -> None:
    data = {
        "ip": "203.0.113.10",
        "asn": "AS12345",
        "as_name": "Example Networks",
        "as_domain": "example.net",
        "country_code": "US",
        "country": "United States",
        "continent_code": "NA",
        "continent": "North America",
    }

    info = SimpleIpInfo(**data)

    for key, value in data.items():
        assert value == getattr(info, key)


class MockResponse:
    def __init__(
        self, payload: dict[str, str], url: str, status_code: int = 200
    ) -> None:
        self._payload = payload
        self._url = url
        self.status_code = status_code

    def json(self) -> dict[str, str]:
        return self._payload

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            request = httpx.Request("GET", self._url)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code} error", request=request, response=response
            )


class MockAsyncClient:
    def __init__(
        self,
        payload: dict[str, str],
        *,
        status_code: int = 200,
        exception: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._status_code = status_code
        self._exception = exception
        self.requests: list[tuple[str, dict[str, str]]] = []

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def get(
        self, url: str, params: dict[str, str], timeout: float | int | None = None
    ) -> MockResponse:
        self.requests.append((url, params))
        if self._exception:
            raise self._exception
        return MockResponse(self._payload, url, status_code=self._status_code)


@pytest.mark.asyncio
async def test_ip_info_client_fetch_simple_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "ip": "198.51.100.7",
        "asn": "AS54321",
        "as_name": "Demo ISP",
        "as_domain": "demo.isp",
        "country_code": "DE",
        "country": "Germany",
        "continent_code": "EU",
        "continent": "Europe",
    }
    mock_client = MockAsyncClient(payload)

    def fake_async_client(**kwargs) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("extip.utils.AsyncClient", fake_async_client)

    client = IpInfoClient(token="secret-token")

    result = await client.fetch_simple_data()

    assert result == SimpleIpInfo(**payload)
    assert mock_client.requests == [
        ("https://api.ipinfo.io/lite/me", {"token": "secret-token"})
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [403, 404])
async def test_ip_info_client_fetch_simple_data_http_errors(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    payload = {}
    mock_client = MockAsyncClient(payload, status_code=status_code)

    def fake_async_client(**kwargs) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("extip.utils.AsyncClient", fake_async_client)
    client = IpInfoClient(token="secret-token")

    with pytest.raises(IpInfoClientError):
        await client.fetch_simple_data()

    assert mock_client.requests == [
        ("https://api.ipinfo.io/lite/me", {"token": "secret-token"})
    ]


@pytest.mark.asyncio
async def test_ip_info_client_fetch_simple_data_connection_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "https://api.ipinfo.io/lite/me")
    timeout_error = httpx.ConnectTimeout("Unable to connect", request=request)
    mock_client = MockAsyncClient({}, exception=timeout_error)

    def fake_async_client(**kwargs) -> MockAsyncClient:
        return mock_client

    monkeypatch.setattr("extip.utils.AsyncClient", fake_async_client)
    client = IpInfoClient(token="secret-token")

    with pytest.raises(IpInfoClientTimeout):
        await client.fetch_simple_data()

    assert mock_client.requests == [
        ("https://api.ipinfo.io/lite/me", {"token": "secret-token"})
    ]
