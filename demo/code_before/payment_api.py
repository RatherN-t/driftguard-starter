from dataclasses import dataclass

@dataclass
class Response:
    status_code: int
    body: dict


def checkout(request, provider) -> Response:
    result = provider.charge(request.payment_method, request.amount)
    if result.success:
        return Response(200, {"status": "paid"})
    return Response(402, {"status": "failed"})
