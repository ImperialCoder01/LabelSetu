/**
 * BarcodeScanner — live camera barcode scanner component.
 *
 * Renders a live camera feed with a scan button. When a barcode is
 * detected (via native BarcodeDetector or Quagga2 fallback), it calls
 * onDetected(barcode).
 *
 * Props:
 *   onDetected(code: string) — called when a barcode is found
 *   onCancel()               — called when user cancels scanning
 *   onError(message: string) — called on camera/scan errors
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { scanBarcode } from "../lib/barcodeDetector";

export default function BarcodeScanner({ onDetected, onCancel, onError }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [scanning, setScanning] = useState(false);
  const [status, setStatus] = useState("Initializing camera...");

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment", // prefer rear camera
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setStatus("Point at a barcode and tap Scan");
    } catch (err) {
      onError?.("Camera access denied or unavailable. Please check permissions.");
    }
  }, [onError]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, [startCamera, stopCamera]);

  const handleScan = async () => {
    if (scanning) return;
    setScanning(true);
    setStatus("Scanning...");

    try {
      const code = await scanBarcode(videoRef.current);
      if (code) {
        stopCamera();
        onDetected?.(code);
      } else {
        setStatus("No barcode detected. Try again or adjust angle.");
      }
    } catch (err) {
      onError?.("Barcode scanning failed. Try uploading a photo instead.");
    } finally {
      setScanning(false);
    }
  };

  const handleCancel = () => {
    stopCamera();
    onCancel?.();
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">
        Scan Barcode
      </h2>

      {/* Camera feed */}
      <div className="relative rounded-lg overflow-hidden bg-black mb-3">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full max-h-64 object-cover"
        />
        {/* Scan overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-3/5 h-1/2 border-2 border-white/60 rounded-lg">
            {/* Corner marks */}
            <div className="absolute -top-0.5 -left-0.5 w-6 h-6 border-t-3 border-l-3 border-primary-400 rounded-tl-lg" />
            <div className="absolute -top-0.5 -right-0.5 w-6 h-6 border-t-3 border-r-3 border-primary-400 rounded-tr-lg" />
            <div className="absolute -bottom-0.5 -left-0.5 w-6 h-6 border-b-3 border-l-3 border-primary-400 rounded-bl-lg" />
            <div className="absolute -bottom-0.5 -right-0.5 w-6 h-6 border-b-3 border-r-3 border-primary-400 rounded-br-lg" />
          </div>
        </div>
      </div>

      {/* Status text */}
      <p className="text-sm text-gray-500 text-center mb-4">{status}</p>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleCancel}
          className="flex-1 py-2.5 px-4 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex-1 py-2.5 px-4 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {scanning ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Scanning...
            </span>
          ) : (
            "Scan"
          )}
        </button>
      </div>

      {/* Manual entry fallback */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-400 text-center mb-2">
          Can&apos;t scan? Enter barcode manually:
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const val = e.target.elements.barcode.value.trim();
            if (/^\d{8,13}$/.test(val)) {
              stopCamera();
              onDetected?.(val);
            }
          }}
          className="flex gap-2"
        >
          <input
            name="barcode"
            type="text"
            inputMode="numeric"
            pattern="\d{8,13}"
            placeholder="e.g. 5449000000996"
            className="input-field flex-1 text-sm"
            maxLength={13}
          />
          <button type="submit" className="btn-primary text-sm px-4">
            Lookup
          </button>
        </form>
      </div>
    </div>
  );
}
