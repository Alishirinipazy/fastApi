import httpx

from app.core.config import settings


class SmsService:
    BASE_URL = "https://api.sms.ir/v1/send/verify"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.SMS_IR_API_KEY

    def send_otp(
        self,
        mobile: str,
        code: str,
        template_id: int = 100000,  
    ) -> None:
        if not self.api_key:
            print(f"[dev] would send OTP {code} to {mobile} via SMS.ir")
            return

        response = httpx.post(
            self.BASE_URL,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "mobile": mobile,
                "templateId": template_id,
                "parameters": [
                    {
                        "name": "Code",
                        "value": code,
                    }
                ],
            },
            timeout=10.0,
        )

        response.raise_for_status()
sms_service = SmsService()