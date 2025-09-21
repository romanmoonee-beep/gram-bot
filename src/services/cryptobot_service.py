import aiohttp
import hashlib
import hmac
from typing import Optional, Dict, Any
import structlog

from app.config.settings import settings

logger = structlog.get_logger(__name__)

class CryptoBotService:
    """Сервис для работы с CryptoBot API"""
    
    def __init__(self):
        self.api_token = settings.CRYPTOBOT_API_TOKEN
        self.webhook_secret = settings.CRYPTOBOT_WEBHOOK_SECRET
        self.base_url = "https://pay.crypt.bot/api"
    
    async def create_invoice(
        self,
        amount: float,
        currency: str,
        description: str,
        payload: str,
        return_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Создать инвойс в CryptoBot"""
        
        data = {
            "currency_type": "crypto",
            "asset": currency,
            "amount": str(amount),
            "description": description,
            "payload": payload,
            "paid_btn_name": "callback",
            "paid_btn_url": return_url or f"https://t.me/{settings.BOT_USERNAME}"
        }
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/createInvoice",
                    json=data,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        logger.info(
                            "💎 CryptoBot invoice created",
                            invoice_id=result["result"]["invoice_id"],
                            amount=amount,
                            currency=currency
                        )
                        return result["result"]
                    else:
                        logger.error(
                            "❌ CryptoBot invoice creation failed",
                            error=result.get("error"),
                            status=response.status
                        )
                        return None
                        
        except Exception as e:
            logger.error("💥 CryptoBot API error", error=str(e), exc_info=True)
            return None
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об инвойсе"""
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/getInvoices",
                    params={"invoice_ids": invoice_id},
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        invoices = result["result"]["items"]
                        return invoices[0] if invoices else None
                    else:
                        logger.error(
                            "❌ CryptoBot get invoice failed",
                            error=result.get("error"),
                            invoice_id=invoice_id
                        )
                        return None
                        
        except Exception as e:
            logger.error("💥 CryptoBot API error", error=str(e), exc_info=True)
            return None
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Получить баланс кошелька"""
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/getBalance",
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        return result["result"]
                    else:
                        logger.error("❌ CryptoBot get balance failed", error=result.get("error"))
                        return None
                        
        except Exception as e:
            logger.error("💥 CryptoBot API error", error=str(e), exc_info=True)
            return None
    
    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Проверить подпись webhook"""
        if not self.webhook_secret:
            return False
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def get_supported_currencies(self) -> Optional[list]:
        """Получить список поддерживаемых валют"""
        
        headers = {
            "Crypto-Pay-API-Token": self.api_token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/getCurrencies",
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        return result["result"]
                    else:
                        logger.error("❌ CryptoBot get currencies failed", error=result.get("error"))
                        return None
                        
        except Exception as e:
            logger.error("💥 CryptoBot API error", error=str(e), exc_info=True)
            return None
