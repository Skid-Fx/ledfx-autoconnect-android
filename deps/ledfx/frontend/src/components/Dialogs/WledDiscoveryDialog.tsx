import { useState, useEffect, useRef } from 'react'
import { Ledfx } from '../../api/ledfx'
import {
  Dialog, DialogActions, DialogContent, DialogTitle,
  Button, List, ListItemButton, ListItemText, Typography
} from '@mui/material'

interface WledDiscoveryDialogProps {
  open: boolean
  onClose: () => void
  onSelect: (ipAddress: string) => void
}

const WledDiscoveryDialog = ({
  open,
  onClose,
  onSelect
}: WledDiscoveryDialogProps) => {
  const [devices, setDevices] = useState<
    { name: string; ip_address: string; version: string; already_added?: boolean }[]
  >([])
  const [selectedIp, setSelectedIp] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const [progress, setProgress] = useState('')
  const [networks, setNetworks] = useState<string[]>([])
  const scanSessionRef = useRef(0)
  const wasOpenRef = useRef(false)
  const scanStoppedRef = useRef(true)
  const scanStartPromiseRef = useRef<Promise<any> | null>(null)

  useEffect(() => {
    if (wasOpenRef.current && !open && !scanStoppedRef.current) {
      scanStoppedRef.current = true
      ++scanSessionRef.current
      setScanning(false)
      const pendingStart = scanStartPromiseRef.current
      void (async () => {
        if (pendingStart) {
          await pendingStart
        }
        await Ledfx('/api/wled_scan', 'DELETE')
      })()
    }
    wasOpenRef.current = open
  }, [open])

  const startScan = async () => {
    const session = ++scanSessionRef.current
    scanStoppedRef.current = false

    setDevices([])
    setSelectedIp(null)
    setScanError(null)
    setProgress('')
    setNetworks([])
    setScanning(true)

    const startPromise = Ledfx('/api/wled_scan', 'POST')
    scanStartPromiseRef.current = startPromise

    const response = await startPromise

    if (scanStartPromiseRef.current === startPromise) {
      scanStartPromiseRef.current = null
    }

    if (session !== scanSessionRef.current) return

    if (!response || response.status !== 'success') {
      setScanError('Could not start the WLED discovery API.')
      setScanning(false)
    }
  }

  const checkScanStatus = async () => {
    const session = scanSessionRef.current
    const response = await Ledfx('/api/wled_scan', 'GET')

    if (session !== scanSessionRef.current) return

    if (response?.status === 'success' && response.data) {
      const found = response.data.devices || []
      setDevices(found)
      setScanning(response.data.scanning === true)
      setScanError(response.data.error || null)
      setNetworks(response.data.networks || [])
      setProgress(
        `${response.data.scanned || 0} / ${response.data.total || 0} addresses checked`
      )
    } else {
      setScanError('Could not retrieve WLED scan results.')
      setScanning(false)
    }
  }

  useEffect(() => {
    if (open) {
      startScan()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (!open || !scanning) return

    const timer = window.setInterval(() => {
      void checkScanStatus()
    }, 1000)

    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, scanning])

  const stopScan = async () => {
    if (scanStoppedRef.current) return

    scanStoppedRef.current = true
    ++scanSessionRef.current
    setScanning(false)

    const pendingStart = scanStartPromiseRef.current
    if (pendingStart) {
      await pendingStart
    }

    await Ledfx('/api/wled_scan', 'DELETE')
  }

  const handleCancel = async () => {
    await stopScan()
    setSelectedIp(null)
    onClose()
  }

  const handleAdd = async () => {
    if (!selectedIp) return

    const ipAddress = selectedIp
    await stopScan()
    onSelect(ipAddress)
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleCancel} fullWidth maxWidth="sm">
      <DialogTitle>Discover WLED Devices</DialogTitle>
      <DialogContent>
        {scanning && (
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            Scanning for WLED devices... {progress}
          </Typography>
        )}
        {scanError && (
          <Typography color="error" sx={{ mb: 1 }}>
            {scanError}
          </Typography>
        )}
        {!scanning && !scanError && devices.length === 0 && (
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            No WLED devices found.
          </Typography>
        )}
        {networks.length > 0 && (
          <Typography variant="caption" color="text.secondary">
            Networks: {networks.join(', ')}
          </Typography>
        )}
        {devices.length > 0 && (
          <List>
            {devices.map((device) => (
              <ListItemButton
                key={device.ip_address}
                selected={selectedIp === device.ip_address}
                disabled={device.already_added === true}
                onClick={() => setSelectedIp(device.ip_address)}
              >
                <ListItemText
                  primary={device.name}
                  secondary={`${device.ip_address} | WLED ${device.version}${device.already_added ? ' | Already Added' : ''}`}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancel}>CANCEL</Button>
        <Button
          onClick={handleAdd}
          disabled={!selectedIp}
          color="primary"
        >
          ADD
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default WledDiscoveryDialog
