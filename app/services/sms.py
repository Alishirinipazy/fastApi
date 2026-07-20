import httpx

from app.core.config import settings


class SmsService:
    """
    Sends the OTP code via Ghasedak, replacing the Laravel SmsChannel +
    OTPSms notification pair. The Laravel side called the official
    `ghasedak/laravel` package's ->Verify($receptor, $type, $template, $param1).

    There's no first-party Ghasedak Python SDK, so this calls their REST
    endpoint directly with httpx. Double-check the endpoint/payload shape
    against Ghasedak's current REST docs before relying on this in
    production - OTP-provider APIs do change, and this is a best-effort
    translation of the PHP SDK call, not a copy of a verified working
    integration.
    """

    BASE_URL = "https://api.ghasedak.me/v2/verification/send"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GHASEDAK_API_KEY

    def send_otp(self, receptor: str, code: str, template: str = "otp") -> None:
        if not self.api_key:
            # Local/dev fallback so auth flow is testable without real credentials.
            print(f"[dev] would send OTP {code} to {receptor} via Ghasedak")
            return

        response = httpx.post(
            self.BASE_URL,
            headers={"apikey": self.api_key},
            json={
                "receptor": receptor,
                "type": "1",
                "template": template,
                "param1": code,
            },
            timeout=10.0,
        )
        response.raise_for_status()


sms_service = SmsService()
