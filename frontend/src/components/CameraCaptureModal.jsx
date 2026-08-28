import { useState, useRef, useEffect, useCallback } from "react";

/**
 * CameraCaptureModal — Desktop & Mobile WebCam packaging photo capture modal.
 *
 * Provides a live webcam viewfinder for PC/desktop and compatible browsers,
 * allowing direct packaging photo capture into the LabelSetu multi-image evidence pipeline.
 * Includes camera rotation/switch support (Rear/Front or Multi-camera switching).
 *
 * Props:
 *   isOpen (boolean): controls modal visibility
 *   onCapture (function(File)): receives captured JPEG File object
 *   onClose (function): called when modal is dismissed
 *   onFallbackUpload (function): triggers fallback file picker if camera unavailable
 */
export default function CameraCaptureModal({ isOpen, onCapture, onClose, onFallbackUpload }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraStatus, setCameraStatus] = useState("INITIALIZING"); // INITIALIZING | READY | ERROR
  const [errorMessage, setErrorMessage] = useState("");
  const [isCapturing, setIsCapturing] = useState(false);
  const [facingMode, setFacingMode] = useState("environment"); // "environment" | "user"
  const [videoDevices, setVideoDevices] = useState([]);
  const [currentDeviceIndex, setCurrentDeviceIndex] = useState(0);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (_) {}
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Enumerate all available camera video input devices
  const updateDeviceList = useCallback(async () => {
    if (!navigator?.mediaDevices?.enumerateDevices) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter((d) => d.kind === "videoinput");
      setVideoDevices(videoInputs);
    } catch (_) {}
  }, []);

  const startCamera = useCallback(async (mode = facingMode, deviceId = null) => {
    stopCamera();
    setCameraStatus("INITIALIZING");
    setErrorMessage("");

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraStatus("ERROR");
      setErrorMessage("Camera access is not supported by your browser or environment. Please use file upload.");
      return;
    }

    try {
      let constraints = {
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      };

      if (deviceId) {
        constraints.video.deviceId = { exact: deviceId };
      } else {
        constraints.video.facingMode = { ideal: mode };
      }

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (_) {
        // Fallback to basic video constraint if specific device/resolution fails
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraStatus("READY");
      await updateDeviceList();
    } catch (err) {
      console.warn("[CameraCaptureModal] Camera initialization error:", err);
      setCameraStatus("ERROR");
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Camera permission was denied. Please allow camera permissions in your browser or select photos from your device.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setErrorMessage("No camera device was detected on your computer. Please connect a webcam or browse files.");
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        setErrorMessage("Camera is currently in use by another application. Please close other camera apps and retry.");
      } else {
        setErrorMessage(`Unable to access camera (${err.message || "Unknown error"}). Please upload a photo instead.`);
      }
    }
  }, [facingMode, stopCamera, updateDeviceList]);

  // Toggle/switch to next camera device or flip front/rear facing mode
  const handleSwitchCamera = useCallback(() => {
    if (videoDevices.length > 1) {
      const nextIndex = (currentDeviceIndex + 1) % videoDevices.length;
      setCurrentDeviceIndex(nextIndex);
      const nextDevice = videoDevices[nextIndex];
      startCamera(facingMode, nextDevice.deviceId);
    } else {
      const nextMode = facingMode === "environment" ? "user" : "environment";
      setFacingMode(nextMode);
      startCamera(nextMode);
    }
  }, [videoDevices, currentDeviceIndex, facingMode, startCamera]);

  useEffect(() => {
    if (isOpen) {
      startCamera(facingMode);
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [isOpen]);

  // Handle ESC key to dismiss modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        stopCamera();
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, stopCamera]);

  const handleCapturePhoto = () => {
    if (!videoRef.current || cameraStatus !== "READY" || isCapturing) return;
    setIsCapturing(true);

    try {
      const video = videoRef.current;
      const width = video.videoWidth || 1280;
      const height = video.videoHeight || 720;

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not create canvas context");

      ctx.drawImage(video, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            setIsCapturing(false);
            return;
          }
          const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
          const capturedFile = new File([blob], `packaging_photo_${timestamp}.jpg`, {
            type: "image/jpeg",
            lastModified: Date.now(),
          });

          stopCamera();
          setIsCapturing(false);
          onCapture?.(capturedFile);
        },
        "image/jpeg",
        0.92
      );
    } catch (err) {
      console.error("[CameraCaptureModal] Capture error:", err);
      setIsCapturing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl text-white flex flex-col">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-base">
              📷
            </span>
            <div>
              <h3 className="text-sm sm:text-base font-black text-white tracking-tight">
                Capture Packaging Photo
              </h3>
              <p className="text-[11px] text-slate-400">
                Align MRP, Mfg Date, or Net Qty panel within frame
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Switch Camera Button in Header */}
            {cameraStatus === "READY" && (
              <button
                type="button"
                onClick={handleSwitchCamera}
                title="Switch Camera (Flip / Next Camera)"
                className="h-8 px-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center gap-1.5 text-xs font-bold transition-all active:scale-95"
              >
                <span>🔄</span>
                <span className="hidden sm:inline">Switch</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                stopCamera();
                onClose?.();
              }}
              className="w-8 h-8 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-sm font-bold transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Viewport Body */}
        <div className="p-4 sm:p-5 flex flex-col items-center">
          <div className="relative w-full aspect-4/3 sm:aspect-16/10 bg-black rounded-2xl overflow-hidden border border-slate-800 flex items-center justify-center">
            {cameraStatus === "INITIALIZING" && (
              <div className="flex flex-col items-center gap-3 text-slate-400 text-xs">
                <div className="w-8 h-8 rounded-full border-2 border-emerald-500/30 border-t-emerald-400 animate-spin" />
                <span>Connecting to camera...</span>
              </div>
            )}

            {cameraStatus === "ERROR" && (
              <div className="p-6 text-center max-w-xs space-y-3">
                <span className="text-3xl">⚠️</span>
                <p className="text-xs text-amber-300 font-medium leading-relaxed">
                  {errorMessage}
                </p>
                {onFallbackUpload && (
                  <button
                    type="button"
                    onClick={() => {
                      stopCamera();
                      onClose?.();
                      onFallbackUpload();
                    }}
                    className="btn-primary text-xs py-2 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow"
                  >
                    📁 Browse Photos from Computer
                  </button>
                )}
              </div>
            )}

            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover transition-opacity duration-300 ${
                cameraStatus === "READY" ? "opacity-100" : "opacity-0 absolute"
              }`}
            />

            {/* Target Reticle Overlay */}
            {cameraStatus === "READY" && (
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center p-6">
                <div className="w-full h-full border-2 border-emerald-400/40 border-dashed rounded-xl relative">
                  {/* Corner brackets */}
                  <div className="absolute -top-1 -left-1 w-5 h-5 border-t-3 border-l-3 border-emerald-400 rounded-tl" />
                  <div className="absolute -top-1 -right-1 w-5 h-5 border-t-3 border-r-3 border-emerald-400 rounded-tr" />
                  <div className="absolute -bottom-1 -left-1 w-5 h-5 border-b-3 border-l-3 border-emerald-400 rounded-bl" />
                  <div className="absolute -bottom-1 -right-1 w-5 h-5 border-b-3 border-r-3 border-emerald-400 rounded-br" />
                </div>
              </div>
            )}

            {/* Floating Quick-Switch Camera Overlay Button */}
            {cameraStatus === "READY" && (
              <button
                type="button"
                onClick={handleSwitchCamera}
                title="Switch Camera"
                className="absolute top-3 right-3 p-2 rounded-xl bg-slate-950/70 hover:bg-slate-900 text-white backdrop-blur-sm border border-slate-700 shadow-md flex items-center gap-1.5 text-xs font-semibold transition-all active:scale-95"
              >
                <span className="text-sm">🔄</span>
                <span className="text-[10px] font-mono uppercase tracking-wide">
                  {videoDevices.length > 1
                    ? `Cam ${currentDeviceIndex + 1}/${videoDevices.length}`
                    : facingMode === "environment"
                    ? "Rear"
                    : "Front"}
                </span>
              </button>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="p-4 sm:p-5 border-t border-slate-800 bg-slate-900/60 flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              stopCamera();
              onClose?.();
            }}
            className="flex-1 py-2.5 px-4 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white font-bold text-xs transition-colors"
          >
            Cancel
          </button>

          {cameraStatus === "READY" && (
            <>
              <button
                type="button"
                onClick={handleSwitchCamera}
                className="py-2.5 px-3 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-300 hover:text-white font-bold text-xs flex items-center gap-1.5 transition-colors"
                title="Switch / Rotate Camera"
              >
                <span>🔄</span>
                <span className="hidden sm:inline">Flip</span>
              </button>

              <button
                type="button"
                onClick={handleCapturePhoto}
                disabled={isCapturing}
                className="flex-2 py-2.5 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-black text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/60 transition-all active:scale-95"
              >
                {isCapturing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    <span>Capturing...</span>
                  </>
                ) : (
                  <>
                    <span>📸</span>
                    <span>Capture Photo</span>
                  </>
                )}
              </button>
            </>
          )}

          {cameraStatus === "ERROR" && onFallbackUpload && (
            <button
              type="button"
              onClick={() => {
                stopCamera();
                onClose?.();
                onFallbackUpload();
              }}
              className="flex-2 py-2.5 px-5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs transition-colors"
            >
              Browse Files
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
