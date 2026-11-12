import asyncio
import logging
import socket
import ipaddress

import aiohttp

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import (
    AsyncServiceBrowser,
    AsyncServiceInfo,
    AsyncZeroconf,
)

from ledfx.events import Event
from ledfx.utils import async_fire_and_forget

_LOGGER = logging.getLogger(__name__)


class ZeroConfRunner:
    """
    Class responsible for handling zeroconf, WLED discovery and WLED device registration.

    Attributes:
        aiobrowser: The async service browser for zeroconf.
        aiozc: The async zeroconf instance.
        _ledfx: The ledfx instance.

    Methods:
        on_service_state_change: Callback function for service state change.
        async_on_service_state_change: Asynchronous function for handling WLED service state change.
        add_wled_device: Asynchronous function for adding discovered WLED devices to config.
        discover_wled_devices: Asynchronous function for discovering WLED devices.
        async_close: Asynchronous function for closing zeroconf listener.
    """

    def __init__(self, ledfx):
        self.aiobrowser = None
        self.aiozc = None
        self._ledfx = ledfx
        self._scan_in_progress = False
        self._monitor_task = None
        self._monitor_task = self._ledfx.loop.create_task(
            self.monitor_wled_connections()
        )

        def on_shutdown(e):
            async_fire_and_forget(self.async_close(), self._ledfx.loop)

        self._ledfx.events.add_listener(on_shutdown, Event.LEDFX_SHUTDOWN)

    def on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ):
        """
        Callback function for service state change.

        Args:
            zeroconf (Zeroconf): The zeroconf instance.
            service_type (str): The service type.
            name (str): The service name.
            state_change (ServiceStateChange): The state change event.
        """
        # Schedule the coroutine to be run on the event loop
        async_fire_and_forget(
            self.async_on_service_state_change(
                zeroconf=zeroconf,
                service_type=service_type,
                name=name,
                state_change=state_change,
            ),
            self._ledfx.loop,
        )

    async def async_on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ):
        """
        Asynchronous function for handling service state change.

        Args:
            zeroconf (Zeroconf): The zeroconf instance.
            service_type (str): The service type.
            name (str): The service name.
            state_change (ServiceStateChange): The state change event.
        """
        _LOGGER.debug(
            f"Service {name} of type {service_type} state changed: {state_change}"
        )
        if state_change is not ServiceStateChange.Added:
            return

        async_fire_and_forget(
            self.add_wled_device(zeroconf, service_type, name),
            self._ledfx.loop,
        )

    async def add_wled_device(
        self, zeroconf: Zeroconf, service_type: str, name: str
    ) -> None:
        """
        Asynchronous function for feeding discovered WLED devices to add_new_device.

        Duplicate detection is handled within add_new_device.

        Args:
            zeroconf (Zeroconf): The zeroconf instance.
            service_type (str): The service type.
            name (str): The service name.
        """
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        if info:
            hostname = str(info.server).rstrip(".")
            _LOGGER.info(f"Found WLED device: {hostname}")

            addresses = info.parsed_addresses()
            discovered_address = addresses[0] if addresses else hostname

            if await self.match_wled_device(discovered_address):
                _LOGGER.info(
                    "Existing WLED device matched via mDNS: %s",
                    discovered_address,
                )
                return
            device_type = "wled"
            device_config = {"ip_address": discovered_address}

            def handle_exception(future):
                # Ignore exceptions, these will be raised when a device is found that already exists
                future.exception()

            async_fire_and_forget(
                self._ledfx.devices.add_new_device(device_type, device_config),
                loop=self._ledfx.loop,
                exc_handler=handle_exception,
            )

    async def identify_wled(self, ip_address):
        """Identify a WLED controller by its IP address."""
        url = f"http://{ip_address}/json/info"

        try:
            timeout = aiohttp.ClientTimeout(total=3)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None

                    info = await response.json()

            mac = info.get("mac")
            if not mac:
                return None

            return {
                "ip_address": ip_address,
                "mac_address": str(mac).upper(),
                "name": info.get("name", "WLED"),
            }

        except (aiohttp.ClientError, TimeoutError, ValueError):
            return None


    async def match_wled_device(self, ip_address):
        """Match a discovered WLED controller to an existing device."""
        info = await self.identify_wled(ip_address)

        if info is None:
            return False

        mac_address = info["mac_address"]

        matched = await self._ledfx.devices.update_wled_ip_by_mac(
            mac_address,
            ip_address,
        )

        if matched:
            _LOGGER.info(
                "Matched WLED %s at %s",
                mac_address,
                ip_address,
            )

        return matched


    def get_network_interfaces(self):
        """Return active IPv4 network interfaces on Android."""
        interfaces = []

        try:
            from jnius import autoclass

            NetworkInterface = autoclass("java.net.NetworkInterface")
            enumeration = NetworkInterface.getNetworkInterfaces()

            while enumeration.hasMoreElements():
                interface = enumeration.nextElement()

                if not interface.isUp() or interface.isLoopback():
                    continue

                addresses = interface.getInterfaceAddresses()

                for index in range(addresses.size()):
                    interface_address = addresses.get(index)
                    address = interface_address.getAddress()
                    ip = str(address.getHostAddress())
                    prefix_length = int(interface_address.getNetworkPrefixLength())

                    try:
                        parsed = ipaddress.ip_address(ip)
                    except ValueError:
                        continue

                    if isinstance(parsed, ipaddress.IPv4Address):
                        if parsed.is_private and not parsed.is_loopback:
                            interfaces.append({
                                "name": str(interface.getName()),
                                "ip_address": ip,
                                "prefix_length": prefix_length,
                            })
                            _LOGGER.info(
                                "Android network interface: %s, IP: %s, prefix: /%s",
                                interface.getName(),
                                ip,
                                prefix_length,
                            )

        except Exception:
            _LOGGER.exception("Unable to enumerate Android network interfaces")

        return interfaces


    def get_scan_networks(self):
        """Calculate IPv4 networks from active interfaces."""
        networks = set()

        for interface in self.get_network_interfaces():
            try:
                ip = interface["ip_address"]
                prefix = interface["prefix_length"]

                network = ipaddress.ip_network(
                    f"{ip}/{prefix}",
                    strict=False,
                )

                if network.is_private and network.num_addresses <= 1024:
                    networks.add(network)

            except (ValueError, KeyError) as error:
                _LOGGER.warning(
                    "Skipping invalid network interface: %s",
                    error,
                )

        return sorted(networks, key=lambda net: int(net.network_address))



    async def scan_wled_networks(self):
        """Scan local networks for existing WLED controllers."""
        if self._scan_in_progress:
            _LOGGER.debug("WLED network scan already running")
            return

        self._scan_in_progress = True

        try:
            networks = self.get_scan_networks()

            if not networks:
                _LOGGER.warning("No suitable networks found for WLED scanning")
                return

            _LOGGER.info(
                "Scanning networks for WLED controllers: %s",
                networks,
            )

            semaphore = asyncio.Semaphore(32)

            async def scan_address(ip):
                async with semaphore:
                    try:
                        matched = await self.match_wled_device(str(ip))
                        if matched:
                            _LOGGER.info(
                                "WLED controller matched at %s",
                                ip,
                            )
                    except Exception:
                        _LOGGER.exception(
                            "Error scanning WLED address %s",
                            ip,
                        )

            tasks = [
                scan_address(ip)
                for network in networks
                for ip in network.hosts()
            ]

            await asyncio.gather(*tasks)

            _LOGGER.info("WLED network scan complete")

        finally:
            self._scan_in_progress = False


    async def monitor_wled_connections(self):
        """Detect WLED IP changes and request rediscovery."""
        _LOGGER.info("WLED connection monitor started")
        last_scan = 0.0

        while True:
            await asyncio.sleep(15)

            if self._scan_in_progress:
                continue

            for device in list(self._ledfx.devices.values()):
                if device.type != "wled":
                    continue

                saved_mac = device.config.get("mac_address", "")
                saved_ip = device.config.get("ip_address", "")

                if not saved_mac or not saved_ip:
                    continue

                info = await self.identify_wled(saved_ip)

                if info is not None:
                    actual_mac = info["mac_address"].replace(":", "").replace("-", "").upper()
                    expected_mac = saved_mac.replace(":", "").replace("-", "").upper()

                    if actual_mac == expected_mac:
                        continue

                now = asyncio.get_running_loop().time()

                if now - last_scan >= 60:
                    last_scan = now
                    _LOGGER.warning(
                        "WLED %s unreachable or MAC mismatch at %s; scanning for new IP",
                        device.name,
                        saved_ip,
                    )
                    await self.scan_wled_networks()

                break

    async def discover_wled_devices(self) -> None:
        """
        Asynchronous function for discovering WLED devices.
        """
        async_fire_and_forget(
            self.scan_wled_networks(),
            loop=self._ledfx.loop,
        )
        if self.aiobrowser is not None:
            _LOGGER.debug("mDNS browser already running")
            return

        self.aiozc = AsyncZeroconf()
        services = ["_wled._tcp.local."]
        _LOGGER.info("Browsing for WLED devices...")
        self.aiobrowser = AsyncServiceBrowser(
            self.aiozc.zeroconf,
            services,
            handlers=[self.on_service_state_change],
        )

    async def async_close(self) -> None:
        """
        Asynchronous function for closing zeroconf listener.
        """
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        # If aiobrowser exists, then aiozc must also exist.
        if self.aiobrowser:
            _LOGGER.info("Closing zeroconf listener.")
            await self.aiobrowser.async_cancel()
            await self.aiozc.async_close()
            _LOGGER.info("Zeroconf closed.")
