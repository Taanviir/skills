from datetime import timedelta

from rapidfuzz import fuzz

DATE_WINDOW = timedelta(days=5)
NAME_THRESHOLD = 85


def matches(payment, invoice):
    return (
        payment.amount == invoice.amount
        and abs(payment.date - invoice.due) <= DATE_WINDOW
        and fuzz.token_set_ratio(payment.payer, invoice.customer) >= NAME_THRESHOLD
    )
