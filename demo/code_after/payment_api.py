from dataclasses import dataclass
from .queue import enqueue
from .store import create_pending_payment

@dataclass
class Response:
    status_code: int
    body: dict


def checkout(request) -> Response:
    payment = create_pending_payment(
        amount=request.amount,
        idempotency_key=request.idempotency_key,
    )
    enqueue("PaymentJob", {"payment_id": payment.id})
    return Response(202, {"payment_id": payment.id, "status": "pending"})
