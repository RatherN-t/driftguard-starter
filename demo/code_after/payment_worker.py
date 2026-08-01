from .store import get_payment, mark_paid, mark_failed


def run_payment_job(payment_id, provider) -> None:
    payment = get_payment(payment_id)
    result = provider.charge(payment.payment_method, payment.amount)
    if result.success:
        mark_paid(payment_id)
    else:
        mark_failed(payment_id)
