/**
 * Device Fingerprinting Utility
 *
 * Generates a unique device fingerprint using Canvas, WebGL, and Audio APIs.
 * This fingerprint is stable across sessions even when cookies are cleared.
 */

export interface DeviceFingerprintData {
  canvasHash: string;
  webglHash: string;
  audioHash: string;
  cpuCores: number;
  memorySize: number;
  screenResolution: string;
  timezone: string;
  language: string;
  userAgent: string;
}

/**
 * Generate SHA-256 hash from a string
 */
async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate Canvas fingerprint
 * Uses various drawing operations to create a unique canvas signature
 */
function getCanvasFingerprint(): string {
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 50;
    const ctx = canvas.getContext('2d');

    if (!ctx) return 'canvas_not_supported';

    // Draw text with gradient
    const gradient = ctx.createLinearGradient(0, 0, 200, 0);
    gradient.addColorStop(0, '#f00');
    gradient.addColorStop(0.5, '#0f0');
    gradient.addColorStop(1, '#00f');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 200, 50);

    // Draw text with various fonts
    ctx.font = '14px Arial';
    ctx.fillStyle = '#000';
    ctx.fillText('Device Fingerprint 123!@#', 10, 20);

    ctx.font = '12px "Times New Roman"';
    ctx.fillStyle = '#fff';
    ctx.fillText('Canvas FP Test', 10, 35);

    // Add emoji (renders differently on different systems)
    ctx.font = '16px sans-serif';
    ctx.fillText('🔒🔐', 150, 25);

    return canvas.toDataURL();
  } catch (e) {
    return 'canvas_error';
  }
}

/**
 * Generate WebGL fingerprint
 * Uses WebGL rendering parameters to create a unique signature
 */
function getWebGLFingerprint(): string {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

    if (!gl) return 'webgl_not_supported';

    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const params: string[] = [];

    // GPU information
    if (debugInfo) {
      params.push(`renderer:${gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)}`);
      params.push(`vendor:${gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)}`);
    }

    // WebGL parameters
    params.push(`version:${gl.getParameter(gl.VERSION)}`);
    params.push(`shading:${gl.getParameter(gl.SHADING_LANGUAGE_VERSION)}`);
    params.push(`max_texture:${gl.getParameter(gl.MAX_TEXTURE_SIZE)}`);
    params.push(`max_vertex:${gl.getParameter(gl.MAX_VERTEX_ATTRIBS)}`);
    params.push(`max_viewport:${JSON.stringify(gl.getParameter(gl.MAX_VIEWPORT_DIMS))}`);

    // Supported extensions
    const extensions = gl.getSupportedExtensions();
    if (extensions) {
      params.push(`extensions:${extensions.sort().join(',')}`);
    }

    return params.join('|');
  } catch (e) {
    return 'webgl_error';
  }
}

/**
 * Generate Audio fingerprint
 * Uses AudioContext to detect audio rendering differences
 */
function getAudioFingerprint(): Promise<string> {
  return new Promise((resolve) => {
    try {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContext) {
        resolve('audio_not_supported');
        return;
      }

      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const analyser = context.createAnalyser();
      const gainNode = context.createGain();
      const scriptProcessor = context.createScriptProcessor(4096, 1, 1);

      gainNode.gain.value = 0; // Mute
      oscillator.type = 'triangle';
      oscillator.frequency.value = 10000;

      oscillator.connect(analyser);
      analyser.connect(scriptProcessor);
      scriptProcessor.connect(gainNode);
      gainNode.connect(context.destination);

      scriptProcessor.onaudioprocess = (event) => {
        const output = event.outputBuffer.getChannelData(0);
        const fingerprint = Array.from(output.slice(0, 30))
          .map(val => val.toFixed(10))
          .join('');

        oscillator.disconnect();
        analyser.disconnect();
        scriptProcessor.disconnect();
        gainNode.disconnect();
        context.close();

        resolve(fingerprint);
      };

      oscillator.start(0);

      // Timeout fallback
      setTimeout(() => {
        resolve('audio_timeout');
      }, 1000);
    } catch (e) {
      resolve('audio_error');
    }
  });
}

/**
 * Get CPU cores count
 */
function getCPUCores(): number {
  return navigator.hardwareConcurrency || 0;
}

/**
 * Get device memory (in GB)
 * Returns approximate memory size in MB
 */
function getMemorySize(): number {
  const deviceMemory = (navigator as any).deviceMemory;
  if (deviceMemory) {
    return deviceMemory * 1024; // Convert GB to MB
  }
  // Estimate based on performance
  return 4096; // Default 4GB
}

/**
 * Get screen resolution
 */
function getScreenResolution(): string {
  return `${window.screen.width}x${window.screen.height}`;
}

/**
 * Get timezone
 */
function getTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Get language
 */
function getLanguage(): string {
  return navigator.language;
}

/**
 * Get user agent
 */
function getUserAgent(): string {
  return navigator.userAgent;
}

/**
 * Generate complete device fingerprint
 */
export async function generateDeviceFingerprint(): Promise<DeviceFingerprintData> {
  const canvasRaw = getCanvasFingerprint();
  const webglRaw = getWebGLFingerprint();
  const audioRaw = await getAudioFingerprint();

  // Hash the raw fingerprints
  const canvasHash = await sha256(canvasRaw);
  const webglHash = await sha256(webglRaw);
  const audioHash = await sha256(audioRaw);

  return {
    canvasHash,
    webglHash,
    audioHash,
    cpuCores: getCPUCores(),
    memorySize: getMemorySize(),
    screenResolution: getScreenResolution(),
    timezone: getTimezone(),
    language: getLanguage(),
    userAgent: getUserAgent(),
  };
}

/**
 * Calculate device ID from fingerprint data
 * This should match the server-side calculation
 */
export async function calculateDeviceId(fingerprint: DeviceFingerprintData): Promise<string> {
  const components = [
    fingerprint.canvasHash,
    fingerprint.webglHash,
    fingerprint.audioHash,
    fingerprint.cpuCores.toString(),
    fingerprint.screenResolution,
    fingerprint.timezone,
    fingerprint.language,
  ];

  const combined = components.join('|');
  return await sha256(combined);
}
