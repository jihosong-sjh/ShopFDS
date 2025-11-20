# Device Fingerprinting Frontend Integration Guide

## Step 1: Import the Provider

Add this import to `src/App.tsx`:

```typescript
import { DeviceFingerprintProvider } from './components/DeviceFingerprintProvider';
```

## Step 2: Wrap the App with the Provider

Update the `App` component to wrap the entire application:

```typescript
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DeviceFingerprintProvider>
        <BrowserRouter>
          <Routes>
            {/* ... existing routes ... */}
          </Routes>
        </BrowserRouter>
      </DeviceFingerprintProvider>
    </QueryClientProvider>
  );
}
```

## Complete Example

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DeviceFingerprintProvider } from './components/DeviceFingerprintProvider';

// ... other imports ...

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DeviceFingerprintProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="register" element={<Register />} />
              <Route path="login" element={<Login />} />
              {/* ... rest of routes ... */}
            </Route>
          </Routes>
        </BrowserRouter>
      </DeviceFingerprintProvider>
    </QueryClientProvider>
  );
}

export default App;
```

## Environment Variables

Add to `.env`:

```env
VITE_FDS_API_URL=http://localhost:8001
```

## Behavior

1. **On App Load**: Device fingerprint is automatically collected and sent to FDS service
2. **Device ID Caching**: Device ID is stored in localStorage to avoid repeated fingerprinting
3. **Blacklist Check**: If device is blacklisted, user sees a blocking screen
4. **Silent Operation**: Fingerprinting happens in the background without user interaction

## Testing

1. Open the app in a browser
2. Check browser console for: `[Device Fingerprint] New device registered: <device_id>`
3. Check localStorage for `device_id` key
4. Blacklist the device via API: `POST /v1/fds/blacklist/device`
5. Refresh the page - should see blocked screen

## API Endpoints Used

- `POST /v1/fds/device-fingerprint/collect` - Submit device fingerprint
- Data sent includes: Canvas hash, WebGL hash, Audio hash, CPU cores, memory, screen resolution, timezone, language, user agent
