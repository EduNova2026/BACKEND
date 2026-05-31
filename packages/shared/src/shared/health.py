def health_response(service: str) -> dict[str, str]:
    return {
        "status": "ok",
        "service": service,
    }
