import httpx

from app.core.config import settings


class ZibalService:
    """
    Thin wrapper around Zibal's request/verify endpoints
    (https://gateway.zibal.ir/v1/...). Replaces app/services/payment.py
    (pay.ir) as the active gateway.
    """

    REQUEST_URL = "https://gateway.zibal.ir/v1/request"
    VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
    START_URL = "https://gateway.zibal.ir/start/{track_id}"

    def __init__(self, merchant: str | None = None):
        self.merchant = merchant or settings.ZIBAL_MERCHANT

    def request(
        self,
        amount_rials: int,
        callback_url: str,
        mobile: str = "",
        order_id: str = "",
        description: str = "",
    ) -> dict:
        response = httpx.post(
            self.REQUEST_URL,
            json={
                "merchant": self.merchant,
                "amount": amount_rials,
                "callbackUrl": callback_url,
                "mobile": mobile,
                "orderId": order_id,
                "description": description,
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return response.json()

    def verify(self, track_id: int) -> dict:
        response = httpx.post(
            self.VERIFY_URL,
            json={"merchant": self.merchant, "trackId": track_id},
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return response.json()

    def start_url(self, track_id: int) -> str:
        return self.START_URL.format(track_id=track_id)


zibal = ZibalService()
