/**
 * Barcode Detection abstraction layer.
 *
 * Uses the native BarcodeDetector API where available (Chrome, Edge,
 * Android WebView), and falls back to @ericblade/quagga2 for other
 * browsers (Firefox, Safari).
 *
 * Usage:
 *   import { scanBarcode } from "../lib/barcodeDetector";
 *   const code = await scanBarcode(videoElement);
 */

import Quagga from "@ericblade/quagga2";

// ---------------------------------------------------------------------------
// Feature detection (lazy — no top-level await)
// ---------------------------------------------------------------------------
const hasNativeBarcodeDetector = typeof BarcodeDetector !== "undefined";

let nativeDetector = null;

async function ensureNativeDetector() {
  if (nativeDetector) return nativeDetector;
  if (!hasNativeBarcodeDetector) return null;
  try {
    const supportedFormats = await BarcodeDetector.getSupportedFormats();
    nativeDetector = new BarcodeDetector({ formats: supportedFormats });
    return nativeDetector;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Native BarcodeDetector path
// ---------------------------------------------------------------------------
async function detectNative(video) {
  const detector = await ensureNativeDetector();
  if (!detector) return null;
  const barcodes = await detector.detect(video);
  if (barcodes.length > 0) {
    return barcodes[0].rawValue;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Quagga2 fallback path
// ---------------------------------------------------------------------------
function detectQuagga(video) {
  return new Promise((resolve, reject) => {
    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;

    Quagga.init(
      {
        inputStream: {
          name: "Live",
          type: "LiveStream",
          target: video,
          size: { width, height },
        },
        decoder: {
          readers: [
            "ean_reader",
            "ean_8_reader",
            "upc_reader",
            "upc_e_reader",
            "code_128_reader",
          ],
        },
        locate: true,
        locator: {
          halfSample: true,
          patchSize: "medium",
        },
      },
      (err) => {
        if (err) {
          reject(err);
          return;
        }
        Quagga.start();
      }
    );

    let resolved = false;

    Quagga.onDetected((result) => {
      if (!resolved && result && result.codeResult) {
        resolved = true;
        Quagga.stop();
        resolve(result.codeResult.code);
      }
    });

    // Timeout after 15 seconds
    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        Quagga.stop();
        resolve(null);
      }
    }, 15000);
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Scan a video element for barcodes.
 * Tries native BarcodeDetector first, falls back to Quagga2.
 *
 * @param {HTMLVideoElement} video - The video element with camera stream
 * @returns {Promise<string|null>} - The detected barcode string, or null
 */
export async function scanBarcode(video) {
  if (!video) return null;

  // Try native first
  if (hasNativeBarcodeDetector) {
    try {
      const result = await detectNative(video);
      if (result) return result;
    } catch {
      // Native detection failed, fall through to Quagga
    }
  }

  // Fall back to Quagga2
  try {
    return await detectQuagga(video);
  } catch {
    return null;
  }
}

/**
 * Check if barcode scanning is available (either native or Quagga).
 */
export function isBarcodeScanningSupported() {
  return hasNativeBarcodeDetector || true; // Quagga2 always available
}
