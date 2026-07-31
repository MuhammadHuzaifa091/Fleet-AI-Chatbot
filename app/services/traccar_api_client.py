import httpx
from app.core.config import settings
from typing import List, Dict, Any, Optional
from loguru import logger


class TraccarAPIClient:
    def __init__(self):
        self.base_url = settings.PC12_API_URL
        self.username = settings.PC12_API_USER
        self.password = settings.PC12_API_PASS
        self._client = httpx.AsyncClient(timeout=15.0)
        self._session_cookie = None

    async def _ensure_session(self):
        if self._session_cookie:
            return
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/session",
                data={"email": self.username, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                jsessionid = resp.cookies.get("JSESSIONID")
                if jsessionid:
                    self._session_cookie = {"JSESSIONID": jsessionid}
                    logger.info(f"[TRACCAR_API] Session established for {self.username}")
                    return
            logger.warning(f"[TRACCAR_API] Login failed for {self.username}: {resp.status_code}")
            logger.warning(f"[TRACCAR_API] Update PC12_API_USER/PC12_API_PASS in .env with correct Traccar credentials")
        except Exception as e:
            logger.warning(f"[TRACCAR_API] Connection failed: {e}")

    async def _request(self, method: str, path: str, **kwargs) -> Optional[Any]:
        await self._ensure_session()
        if not self._session_cookie:
            return None
        cookies = kwargs.pop("cookies", {})
        cookies.update(self._session_cookie)
        try:
            resp = await self._client.request(
                method, f"{self.base_url}/api/{path}",
                cookies=cookies, **kwargs,
            )
            if resp.status_code == 401:
                self._session_cookie = None
                await self._ensure_session()
                if self._session_cookie:
                    cookies.update(self._session_cookie)
                    resp = await self._client.request(
                        method, f"{self.base_url}/api/{path}",
                        cookies=cookies, **kwargs,
                    )
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"[TRACCAR_API] {method} /api/{path} -> {resp.status_code}")
            return None
        except Exception as e:
            logger.warning(f"[TRACCAR_API] Request error: {e}")
            return None

    async def get_devices(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "devices")
        return data if isinstance(data, list) else []

    async def get_positions(self) -> List[Dict[str, Any]]:
        data = await self._request("GET", "positions")
        return data if isinstance(data, list) else []

    async def get_device_positions(self, device_id: int, from_iso: str = None, to_iso: str = None) -> List[Dict[str, Any]]:
        params = {"deviceId": device_id}
        if from_iso:
            params["from"] = from_iso
        if to_iso:
            params["to"] = to_iso
        data = await self._request("GET", "positions", params=params)
        return data if isinstance(data, list) else []

    async def get_events(self, device_id: int = None, event_type: str = None, from_iso: str = None, to_iso: str = None) -> List[Dict[str, Any]]:
        params = {}
        if device_id:
            params["deviceId"] = device_id
        if event_type:
            params["type"] = event_type
        if from_iso:
            params["from"] = from_iso
        if to_iso:
            params["to"] = to_iso
        data = await self._request("GET", "events", params=params)
        return data if isinstance(data, list) else []

    async def get_report_events(self, from_iso: str, to_iso: str, device_id: int = None, all_devices: bool = True) -> List[Dict[str, Any]]:
        params = {"from": from_iso, "to": to_iso}
        if all_devices:
            params["all"] = "true"
        if device_id:
            params["deviceId"] = device_id
        data = await self._request("GET", "reports/events", params=params)
        return data if isinstance(data, list) else []

    async def close(self):
        await self._client.aclose()


_traccar_client: Optional[TraccarAPIClient] = None


async def get_traccar_client() -> TraccarAPIClient:
    global _traccar_client
    if _traccar_client is None:
        _traccar_client = TraccarAPIClient()
    return _traccar_client