from __future__ import annotations

import httpx
from fastapi import HTTPException, Request, Response, status


_REQUEST_HEADERS_TO_SKIP = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "forwarded",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
}

_RESPONSE_HEADERS_TO_SKIP = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _forwarded_request_headers(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _REQUEST_HEADERS_TO_SKIP
    }


def _forwarded_response_headers(response: httpx.Response) -> dict[str, str]:
    return {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in _RESPONSE_HEADERS_TO_SKIP
    }


def create_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


async def proxy_request(request: Request, upstream_url: str) -> Response:
    body = await request.body()

    try:
        async with create_async_client() as client:
            upstream_response = await client.request(
                request.method,
                upstream_url,
                content=body,
                headers=_forwarded_request_headers(request),
                params=request.query_params,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream service unavailable",
        ) from exc

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=_forwarded_response_headers(upstream_response),
    )
