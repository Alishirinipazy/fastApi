import httpx

from app.core.config import settings


class PayIrService:
    """Thin wrapper around pay.ir's send/verify endpoints - a straight port of
    PaymentController::sendRequest/verifyRequest/curl_post."""

    SEND_URL = "https://pay.ir/pg/send"
    VERIFY_URL = "https://pay.ir/pg/verify"
    GATEWAY_URL = "https://pay.ir/pg/{token}"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.PAY_IR_API_KEY

    def send(self, amount_rials: int, redirect: str, mobile: str = "", factor_number: str = "", description: str = ""):
        response = httpx.post(
            self.SEND_URL,
            json={
                "api": self.api_key,
                "amount": amount_rials,
                "redirect": redirect,
                "mobile": mobile,
                "factorNumber": factor_number,
                "description": description,
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0,
            verify=False,  # matches CURLOPT_SSL_VERIFYPEER=false in the original
        )
        return response.json()

    def verify(self, token: str):
        response = httpx.post(
            self.VERIFY_URL,
            json={"api": self.api_key, "token": token},
            headers={"Content-Type": "application/json"},
            timeout=15.0,
            verify=False,
        )
        return response.json()

    def gateway_url(self, token: str) -> str:
        return self.GATEWAY_URL.format(token=token)


pay_ir = PayIrService()
