# app/services/zibal.py
import httpx
from app.core.config import settings


class ZibalService:
    SEND_URL = "https://gateway.zibal.ir/v1/request"
    VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
    GATEWAY_URL = "https://gateway.zibal.ir/start/{track_id}"

    def __init__(self, merchant: str | None = None):
        self.merchant = merchant or settings.ZIBAL_MERCHANT

    def request(
        self,
        amount_rials: int,
        callback_url: str | None = None,
        mobile: str = "",
        order_id: str = "",
        description: str = "",
    ):
        payload = {
            "merchant": self.merchant,
            "amount": amount_rials,
            "callbackUrl": callback_url or settings.PAYMENT_CALLBACK_URL,
        }
        if mobile:
            payload["mobile"] = mobile
        if order_id:
            payload["orderId"] = order_id
        if description:
            payload["description"] = description

        response = httpx.post(
            self.SEND_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return response.json()

    def verify(self, track_id: str | int):
        response = httpx.post(
            self.VERIFY_URL,
            json={
                "merchant": self.merchant,
                "trackId": int(track_id),
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return response.json()

    def start_url(self, track_id: str | int) -> str:
        return self.GATEWAY_URL.format(track_id=track_id)


zibal = ZibalService()