"""Manual WLED discovery for the Add Device dialog."""

import asyncio
import logging

import aiohttp

from ledfx.api import RestEndpoint

_LOGGER = logging.getLogger(__name__)


class WledScanEndpoint(RestEndpoint):
    ENDPOINT_PATH = "/api/wled_scan"

    def __init__(self, ledfx):
        super().__init__(ledfx)
        self._scan_task = None
        self._scan_results = []
        self._scan_error = None
        self._scan_networks = []
        self._scanned = 0
        self._total = 0

    def is_existing_device(self, discovered):
        mac = discovered["mac_address"].replace(":", "").replace("-", "").upper()
        for device in self._ledfx.devices.values():
            if device.type != "wled":
                continue

            config = device.config
            saved_mac = str(config.get("mac_address") or "")
            saved_mac = saved_mac.replace(":", "").replace("-", "").upper()

            if mac and saved_mac and mac == saved_mac:
                return True
            if str(config.get("ip_address")) == discovered["ip_address"]:
                return True

        return False

    async def identify_wled(self, session, address):
        try:
            async with session.get(f"http://{address}/json/info") as response:
                if response.status != 200:
                    return None

                info = await response.json(content_type=None)
                if not isinstance(info, dict) or not info.get("ver"):
                    return None

                device = {
                    "name": str(info.get("name") or "WLED"),
                    "ip_address": str(address),
                    "version": str(info.get("ver") or "Unknown"),
                    "mac_address": str(info.get("mac") or "").upper(),
                }
                device["already_added"] = self.is_existing_device(device)
                return device

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None
        except Exception:
            _LOGGER.exception("WLED probe failed for %s", address)
            return None

    async def scan_devices(self):
        # Reuse the proven AutoConnect network detection, unchanged.
        networks = self._ledfx.zeroconf.get_scan_networks()
        self._scan_networks = [str(network) for network in networks]

        if not networks:
            self._scan_error = (
                "No scannable IPv4 networks detected. "
                "Check Wi-Fi or hotspot connectivity."
            )
            return

        addresses = sorted(
            {str(ip) for network in networks for ip in network.hosts()}
        )
        self._total = len(addresses)
        queue = asyncio.Queue()

        for address in addresses:
            queue.put_nowait(address)

        found = {}
        timeout = aiohttp.ClientTimeout(total=2)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            async def worker():
                while True:
                    try:
                        address = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    try:
                        device = await self.identify_wled(session, address)
                        if device:
                            key = device["mac_address"] or device["ip_address"]
                            found[key] = device
                            self._scan_results = sorted(
                                found.values(),
                                key=lambda item: tuple(
                                    int(part)
                                    for part in item["ip_address"].split(".")
                                ),
                            )
                            _LOGGER.info(
                                "WLED discovery found %s at %s",
                                device["name"],
                                device["ip_address"],
                            )
                    finally:
                        self._scanned += 1
                        queue.task_done()

            tasks = [
                asyncio.create_task(worker())
                for _ in range(min(32, len(addresses)))
            ]

            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

    async def run_scan(self):
        try:
            await self.scan_devices()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            _LOGGER.exception("WLED discovery scan failed")
            self._scan_error = f"Scan failed: {type(error).__name__}: {error}"

    async def post(self, request):
        if self._scan_task is not None and not self._scan_task.done():
            return await self.request_success(data={"scanning": True})

        self._scan_results = []
        self._scan_error = None
        self._scan_networks = []
        self._scanned = 0
        self._total = 0

        self._scan_task = asyncio.create_task(self.run_scan())
        return await self.request_success(data={"scanning": True})

    async def delete(self):
        if self._scan_task is not None and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        self._scan_task = None
        self._scan_results = []

        return await self.request_success(
            data={"devices": [], "scanning": False}
        )

    async def get(self):
        scanning = (
            self._scan_task is not None
            and not self._scan_task.done()
        )

        return await self.request_success(
            data={
                "devices": self._scan_results,
                "scanning": scanning,
                "error": self._scan_error,
                "networks": self._scan_networks,
                "scanned": self._scanned,
                "total": self._total,
            }
        )
