from decimal import Decimal, InvalidOperation

from django.conf import settings


class PaymentError(Exception):
    """Raised when appointment payment is not configured or cannot be verified."""


def configured_appointment_fee():
    raw_fee = getattr(settings, "APPOINTMENT_FEE", "")
    if not raw_fee:
        return None
    try:
        fee = Decimal(str(raw_fee))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentError("APPOINTMENT_FEE must be a positive amount, or left blank to disable payment.") from exc
    if not fee.is_finite() or fee <= 0 or fee.as_tuple().exponent < -2:
        raise PaymentError("APPOINTMENT_FEE must be a positive amount with no more than two decimal places.")
    return fee


def razorpay_test_client():
    try:
        import razorpay
    except ImportError as exc:
        raise PaymentError("Razorpay support is not installed. Install the project requirements first.") from exc
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not key_id.startswith("rzp_test_") or not key_secret:
        raise PaymentError("Payment is enabled, but valid Razorpay test keys are not configured.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_appointment_order(appointment):
    client = razorpay_test_client()
    return client.order.create(data={
        "amount": int(appointment.payment_amount * 100),
        "currency": "INR",
        "receipt": f"mc-{appointment.booking_reference.hex}",
        "notes": {"appointment_reference": str(appointment.booking_reference)},
    })


def verify_appointment_payment(appointment, payment_id, signature):
    client = razorpay_test_client()
    order_id = appointment.razorpay_order_id
    if not order_id or not payment_id or not signature:
        raise PaymentError("Payment confirmation is incomplete.")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        payment = client.payment.fetch(payment_id)
        expected_amount = int(appointment.payment_amount * 100)
        if payment.get("order_id") != order_id:
            raise PaymentError("Payment does not belong to this appointment.")
        if payment.get("amount") != expected_amount or payment.get("currency") != "INR":
            raise PaymentError("The payment amount does not match the appointment fee.")
        if payment.get("status") == "authorized":
            client.payment.capture(payment_id, expected_amount)
            payment = client.payment.fetch(payment_id)
        if payment.get("status") != "captured":
            raise PaymentError("Razorpay has not captured this payment yet.")
    except PaymentError:
        raise
    except Exception as exc:
        raise PaymentError("Razorpay could not verify the payment. Please retry.") from exc
    return payment
