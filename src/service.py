# LedFx AutoConnect background service.
# A partial CPU wake lock keeps real-time DDP output running
# while the Android display is turned off.

def main():
    from jnius import autoclass

    PythonService = autoclass("org.kivy.android.PythonService")
    PowerManager = autoclass("android.os.PowerManager")

    service = PythonService.mService
    power_manager = service.getSystemService("power")

    wake_lock = power_manager.newWakeLock(
        PowerManager.PARTIAL_WAKE_LOCK,
        "LedFxAutoConnect:DDP"
    )

    wake_lock.setReferenceCounted(False)
    wake_lock.acquire()

    try:
        from ledfx_bootstrap import start_ledfx
        start_ledfx()
    finally:
        if wake_lock.isHeld():
            wake_lock.release()


if __name__ == "__main__":
    main()
