# FDS Router Integration Guide

## Add New Routers to main.py

### Step 1: Add Imports

Add these two import lines after line 20 in `services/fds/src/main.py`:

```python
from .api.device_fingerprint import router as device_fingerprint_router
from .api.blacklist import router as blacklist_router
```

### Step 2: Register Routers

Add these two lines after line 86 (after `app.include_router(threat_router)`):

```python
app.include_router(device_fingerprint_router)
app.include_router(blacklist_router)
```

## Complete Updated Section

The router registration section should look like this:

```python
# Router Registration
app.include_router(evaluation_router)
app.include_router(threat_router)
app.include_router(device_fingerprint_router)  # [NEW]
app.include_router(blacklist_router)           # [NEW]
```

## Verify Installation

1. Start FDS service: `cd services/fds && python src/main.py`
2. Check Swagger docs: http://localhost:8001/docs
3. You should see new endpoint groups:
   - **Device Fingerprint**: POST /v1/fds/device-fingerprint/collect, GET /v1/fds/device-fingerprint/{device_id}
   - **Blacklist**: GET/POST/DELETE /v1/fds/blacklist/device/*

## API Endpoints Added

### Device Fingerprint
- `POST /v1/fds/device-fingerprint/collect` - Collect device fingerprint
- `GET /v1/fds/device-fingerprint/{device_id}` - Get device info

### Blacklist
- `GET /v1/fds/blacklist/device/{device_id}` - Check if device is blacklisted
- `POST /v1/fds/blacklist/device` - Add device to blacklist
- `DELETE /v1/fds/blacklist/device/{device_id}` - Remove device from blacklist
- `GET /v1/fds/blacklist/entries` - List all blacklisted devices
- `GET /v1/fds/blacklist/stats` - Get blacklist statistics
