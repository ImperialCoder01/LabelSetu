import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { useAuth } from "../../context/AuthContext";
import BarcodeScanner from "../../components/BarcodeScanner";
import AppDrawer from "../../components/AppDrawer";
import CameraCaptureModal from "../../components/CameraCaptureModal";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

async function optimizeImageForUpload(file, maxDimension = 1600, quality = 0.88) {
  if (!file || !file.type || !file.type.startsWith("image/")) return file;
  return new Promise((resolve) => {
    try {
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(objectUrl);
        let { width, height } = img;
        if (width <= maxDimension && height <= maxDimension) {
          resolve(file);
          return;
        }
        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(file);
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file);
              return;
            }
            const cleanName = file.name ? file.name.replace(/\.[^/.]+$/, ".jpg") : "upload.jpg";
            const optimized = new File([blob], cleanName, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            resolve(optimized);
          },
          "image/jpeg",
          quality
        );
      };
      img.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        resolve(file);
      };
      img.src = objectUrl;
    } catch (_) {
      resolve(file);
    }
  });
}

export default function ScanProductPage() {
  const { role, isAdmin } = useAuth();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [capturedBarcode, setCapturedBarcode] = useState(null);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [barcodeVerifResult, setBarcodeVerifResult] = useState(null);
  const [verifyingBarcode, setVerifyingBarcode] = useState(false);
  const [crossValReport, setCrossValReport] = useState(null);

  const [screen, setScreen] = useState("upload");
  const [lastResult, setLastResult] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [processingStep, setProcessingStep] = useState("OPTIMIZING"); // OPTIMIZING | UPLOADING | AUDITING | AI_RECOVERY
  const isSubmittingRef = useRef(false);
  const activeAbortCtrlRef = useRef(null);

  const [activeRuleDrawer, setActiveRuleDrawer] = useState(null);
  const [ocrDrawerOpen, setOcrDrawerOpen] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [reporting, setReporting] = useState(false);

  const fileRef = useRef(null);
  const cameraRef = useRef(null);
  const [cameraModalOpen, setCameraModalOpen] = useState(false);

  const handleTakePhotoClick = () => {
    const isMobile =
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
      (window.matchMedia && window.matchMedia("(pointer: coarse)").matches && typeof window.ontouchstart !== "undefined");

    if (isMobile && cameraRef.current) {
      cameraRef.current.click();
    } else if (navigator?.mediaDevices?.getUserMedia) {
      setCameraModalOpen(true);
    } else if (cameraRef.current) {
      cameraRef.current.click();
    }
  };

  const handleCameraCapture = (capturedFile) => {
    setSelectedFiles((prev) => {
      const combined = [...prev, capturedFile];
      return combined.slice(0, 5);
    });
    setCameraModalOpen(false);
  };

  const handleInputChange = (e) => {
    if (!e.target.files?.length) return;
    const newFiles = Array.from(e.target.files).filter((f) => f.type.startsWith("image/"));
    setSelectedFiles((prev) => {
      const combined = [...prev, ...newFiles];
      return combined.slice(0, 5);
    });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (!e.dataTransfer.files?.length) return;
    const newFiles = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith("image/"));
    setSelectedFiles((prev) => [...prev, ...newFiles].slice(0, 5));
  };

  const handleRemoveFile = (idx) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  async function handleScan() {
    if (isSubmittingRef.current) return; // Prevent accidental duplicate submissions

    if (isAdmin) {
      setScanError({
        message: "Live packaging audits are authorized for Consumer and Brand accounts. Please sign in with a consumer or brand account.",
        apiHost: API_BASE,
        online: navigator.onLine ? "Yes" : "No",
        imagesCount: selectedFiles.length,
        totalSizeKB: 0,
      });
      return;
    }

    if (selectedFiles.length === 0 && !capturedBarcode) return;

    isSubmittingRef.current = true;
    setScreen("processing");
    setProcessingStep("OPTIMIZING");
    setScanError(null);
    setLastResult(null);

    const totalRawKB = Math.round(selectedFiles.reduce((a, b) => a + (b.size || 0), 0) / 1024);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.access_token) {
        throw new Error("Authentication session expired. Please sign in again.");
      }

      setProcessingStep("OPTIMIZING");
      const filesToUpload = await Promise.all(
        selectedFiles.map((file) => optimizeImageForUpload(file))
      );

      const formData = new FormData();
      filesToUpload.forEach((file) => {
        formData.append("files", file);
      });
      if (capturedBarcode) formData.append("barcode", capturedBarcode);

      setProcessingStep("UPLOADING");

      if (activeAbortCtrlRef.current) {
        activeAbortCtrlRef.current.abort(); // Cancel any previous stale request
      }
      const scanCtrl = new AbortController();
      activeAbortCtrlRef.current = scanCtrl;
      const scanTimer = setTimeout(() => scanCtrl.abort(), 60000);

      // Advance UI stage indicators responsively
      const stepTimer1 = setTimeout(() => setProcessingStep("AUDITING"), 1500);
      const stepTimer2 = setTimeout(() => setProcessingStep("AI_RECOVERY"), 3500);

      const res = await fetch(`${API_BASE}/api/scans/scan`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        body: formData,
        signal: scanCtrl.signal,
      });
      clearTimeout(scanTimer);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      if (!res.ok) {
        let errMessage = `Scanning failed (HTTP ${res.status})`;
        try {
          const errData = await res.json();
          if (errData?.detail) errMessage = errData.detail;
        } catch (_) {}
        throw new Error(errMessage);
      }

      const resultData = await res.json();
      setLastResult(resultData);

      // Perform Physical OCR vs Level 1 Cross-Validation if barcode available
      if (capturedBarcode || resultData.barcode_lookup?.barcode) {
        const bCode = capturedBarcode || resultData.barcode_lookup?.barcode;
        try {
          const cvRes = await fetch(`${API_BASE}/api/verification/cross-validate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              barcode: bCode,
              ocr_text: resultData.ocr?.extracted_text || "",
              extracted_entities: resultData.ocr?.extracted_entities || {},
              scan_id: resultData.scan_id,
            }),
          });
          if (cvRes.ok) {
            const cvData = await cvRes.json();
            setCrossValReport(cvData);
          }
        } catch (cvErr) {
          console.debug("Cross-validation skipped:", cvErr);
        }
      }

      setScreen("results");
    } catch (err) {
      if (err.name === "AbortError" && !isSubmittingRef.current) return; // Silent abort if user navigated
      console.error("Scan error:", err);
      setScanError({
        message: err.name === "AbortError"
          ? "Scan timed out (60s). Please try again with a clearer single image."
          : err.message || "Failed to complete packaging scan.",
        apiHost: API_BASE,
        online: navigator.onLine ? "Yes" : "No",
        imagesCount: selectedFiles.length,
        totalSizeKB: totalRawKB,
      });
      setScreen("upload");
    } finally {
      isSubmittingRef.current = false;
      activeAbortCtrlRef.current = null;
    }
  }

  async function handleReportGrievance() {
    if (!lastResult?.scan_id) return;
    setReporting(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      await fetch(`${API_BASE}/api/reports/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          scan_id: lastResult.scan_id,
          reason: reportReason || "Legal Metrology declaration non-compliance violation.",
        }),
      });
      setReportSuccess(true);
    } catch (err) {
      console.error("Report failed:", err);
    } finally {
      setReporting(false);
    }
  }

  return (
    <div className="space-y-6">
      {isAdmin && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-900 text-xs flex items-start gap-3 shadow-xs">
          <span className="text-xl">🛡️</span>
          <div>
            <p className="font-extrabold text-amber-950">Admin Preview Mode</p>
            <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
              You are viewing this screen as an <strong>Administrator</strong>. Live packaging audits against the backend require a <strong>Consumer</strong> or <strong>Brand</strong> account.
            </p>
          </div>
        </div>
      )}

      {screen === "processing" && (
        <div className="card-slate p-8 sm:p-12 text-center max-w-xl mx-auto space-y-6 animate-fade-in">
          <div className="relative w-20 h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
            <div className="absolute inset-0 rounded-full border-4 border-emerald-600 border-t-transparent animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center text-2xl">
              🔍
            </div>
          </div>

          <div>
            <h3 className="text-xl font-black text-slate-900 tracking-tight">
              Auditing Packaging Declarations...
            </h3>
            <p className="text-xs text-slate-500 mt-1">This usually takes a few seconds.</p>
          </div>

          <div className="space-y-2 text-left bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div className="flex items-center gap-2 text-slate-700 font-bold">
              <span className="text-emerald-600">✓</span> Validating image structure & content
            </div>
            <div className="flex items-center gap-2 text-slate-700 font-bold">
              <span className="text-emerald-600">✓</span> Running optical character recognition (OCR)
            </div>
            <div className="flex items-center gap-2 text-slate-700 font-bold">
              <span className="text-emerald-600">✓</span> Classifying panels & aggregating evidence
            </div>
            <div className="flex items-center gap-2 text-slate-700 font-bold">
              <span className="text-emerald-600">✓</span> Checking Legal Metrology 2011 compliance
            </div>
          </div>
        </div>
      )}

      {screen === "upload" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">Scan Product Packaging</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload 1 to 5 photos of the package panels (Front, Back, Side, MRP Flap)
              </p>
            </div>
            {selectedFiles.length > 0 && (
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                {selectedFiles.length} / 5 Selected
              </span>
            )}
          </div>

          {scanError && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-900 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold">
                <span>⚠️</span> {scanError.message}
              </div>
              <details className="text-[11px] opacity-80 cursor-pointer pt-1">
                <summary className="font-bold">Technical Diagnostics</summary>
                <div className="mt-1 font-mono space-y-0.5 bg-white/60 p-2 rounded-lg">
                  <p>API Base: {scanError.apiHost}</p>
                  <p>Online: {scanError.online}</p>
                  <p>Photos: {scanError.imagesCount} ({scanError.totalSizeKB} KB raw)</p>
                </div>
              </details>
            </div>
          )}

          {selectedFiles.length > 0 ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {selectedFiles.map((file, idx) => (
                  <div key={idx} className="relative rounded-xl border border-slate-200 bg-slate-50 p-2 text-center overflow-hidden">
                    <div className="w-full h-28 bg-slate-200 rounded-lg overflow-hidden flex items-center justify-center mb-1.5">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Preview ${idx + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <p className="text-[11px] font-bold text-slate-800 truncate px-1">{file.name}</p>
                    <p className="text-[10px] text-slate-400 font-mono">{(file.size / 1024).toFixed(0)} KB</p>
                    <span className="absolute top-3 left-3 bg-slate-900/80 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">
                      #{idx + 1}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(idx)}
                      className="absolute top-3 right-3 bg-red-600 hover:bg-red-700 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs shadow-md"
                      title="Remove photo"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>

              {selectedFiles.length < 5 && (
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  className="w-full py-3 border-2 border-dashed border-slate-300 hover:border-slate-400 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50 transition-colors flex items-center justify-center gap-1.5"
                >
                  <span>+</span> Add Another Packaging Photo (e.g. Back or Side Panel)
                </button>
              )}
            </div>
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-10 sm:p-14 text-center cursor-pointer transition-all ${
                dragOver ? "border-emerald-500 bg-emerald-50/50" : "border-slate-300 hover:border-slate-400 hover:bg-slate-50/50"
              }`}
            >
              <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center text-2xl mb-3 shadow-xs">
                📷
              </div>
              <h3 className="text-base font-extrabold text-slate-900">Click or Drag & Drop Packaging Photos</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Upload clear photos showing the brand name, MRP, Net Weight, and Manufacturer address.
              </p>
            </div>
          )}

          <input ref={fileRef} type="file" accept="image/*" multiple onChange={handleInputChange} className="hidden" id="scan-file-input" />
          <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={handleInputChange} className="hidden" id="scan-camera-input" />

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleTakePhotoClick}
              className="btn-secondary flex-1 cursor-pointer"
            >
              <span>📸</span> Take Photo
            </button>
            <label htmlFor="scan-file-input" className="btn-secondary flex-1 cursor-pointer">
              <span>📁</span> Browse Files
            </label>
            <button
              type="button"
              onClick={() => setScannerOpen(!scannerOpen)}
              className={`btn-secondary flex-1 ${capturedBarcode ? "border-emerald-500 text-emerald-700 font-black" : ""}`}
            >
              <span>🔲</span> {capturedBarcode ? `Barcode: ${capturedBarcode}` : "Scan Barcode"}
            </button>
          </div>

          {/* Instant Barcode Authenticity Lookup Result */}
          {barcodeVerifResult && (
            <div className={`p-4 rounded-xl border text-xs space-y-2 ${
              barcodeVerifResult.result === "VERIFIED"
                ? "bg-emerald-50/80 border-emerald-200 text-emerald-950"
                : barcodeVerifResult.result === "SUSPENDED_PRODUCT"
                ? "bg-rose-50 border-rose-200 text-rose-950"
                : "bg-amber-50/80 border-amber-200 text-amber-950"
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-base">{barcodeVerifResult.result === "VERIFIED" ? "🛡️" : "⚠️"}</span>
                  <span className="font-extrabold text-sm">{barcodeVerifResult.message}</span>
                </div>
                <span className={`px-2 py-0.5 rounded font-black text-[10px] uppercase ${
                  barcodeVerifResult.result === "VERIFIED" ? "bg-emerald-200 text-emerald-900" : "bg-amber-200 text-amber-900"
                }`}>
                  {barcodeVerifResult.result}
                </span>
              </div>
              {barcodeVerifResult.verified_product && (
                <div className="bg-white/80 p-3 rounded-lg grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Product</span>
                    <span className="font-bold text-slate-800">{barcodeVerifResult.verified_product.product_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Brand</span>
                    <span className="font-bold text-slate-800">{barcodeVerifResult.verified_product.brand_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Official MRP</span>
                    <span className="font-bold text-emerald-700">{barcodeVerifResult.verified_product.mrp ? `₹${barcodeVerifResult.verified_product.mrp}` : "N/A"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Net Quantity</span>
                    <span className="font-bold text-slate-800">{barcodeVerifResult.verified_product.net_quantity || "N/A"}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          <CameraCaptureModal
            isOpen={cameraModalOpen}
            onCapture={handleCameraCapture}
            onClose={() => setCameraModalOpen(false)}
            onFallbackUpload={() => fileRef.current?.click()}
          />

          {scannerOpen && (
            <div className="card-slate p-4 border-slate-300">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-800">Position barcode in front of camera:</span>
                <button onClick={() => setScannerOpen(false)} className="text-xs font-bold text-slate-500 hover:text-slate-800">
                  ✕ Close Scanner
                </button>
              </div>
              <BarcodeScanner
                onScanSuccess={(code) => {
                  setCapturedBarcode(code);
                  setScannerOpen(false);
                }}
              />
            </div>
          )}

          <div className="card-slate p-4 bg-slate-50/70">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">
              💡 Recommended Packaging Panels for 100% Verification Coverage
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2 bg-white rounded-lg border border-slate-200">
                <p className="font-bold text-slate-800">1. Front Panel</p>
                <p className="text-[11px] text-slate-400">Product Name & Brand</p>
              </div>
              <div className="p-2 bg-white rounded-lg border border-slate-200">
                <p className="font-bold text-slate-800">2. Back Panel</p>
                <p className="text-[11px] text-slate-400">MRP, Net Qty, Mfg Date</p>
              </div>
              <div className="p-2 bg-white rounded-lg border border-slate-200">
                <p className="font-bold text-slate-800">3. Side Panel</p>
                <p className="text-[11px] text-slate-400">Manufacturer Address</p>
              </div>
              <div className="p-2 bg-white rounded-lg border border-slate-200">
                <p className="font-bold text-slate-800">4. Flap / Base</p>
                <p className="text-[11px] text-slate-400">Consumer Care & USP</p>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleScan}
            disabled={(selectedFiles.length === 0 && !capturedBarcode) || isAdmin}
            className={`w-full py-4 text-sm font-black tracking-wide rounded-xl shadow-md transition-all ${
              isAdmin
                ? "bg-slate-200 text-slate-500 cursor-not-allowed border border-slate-300"
                : "btn-accent disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg"
            }`}
          >
            {isAdmin
              ? "Scanning Disabled in Admin View (Sign in as Consumer or Brand)"
              : selectedFiles.length > 1
              ? `Audit ${selectedFiles.length} Packaging Photos`
              : "Audit Packaging Label"}
          </button>
        </div>
      )}

      {screen === "results" && lastResult && (
        <div className="space-y-6 animate-fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900 tracking-tight">Legal Metrology Audit Report</h2>
            <button
              onClick={() => {
                setSelectedFiles([]);
                setLastResult(null);
                setScreen("upload");
              }}
              className="btn-secondary text-xs"
            >
              ← Scan Another Packaging
            </button>
          </div>

          {(() => {
            const comp = lastResult.compliance || {};
            const score = comp.overall_score !== undefined && comp.overall_score !== null ? comp.overall_score : null;
            const completeness = comp.verification_completeness || "ASSESSED";
            const coverage = comp.evidence_coverage || "8/8 declarations assessable";
            const isAssessable = score !== null;
            const isCompliant = isAssessable && score >= 80;
            const isInsufficient = !isAssessable || completeness === "INSUFFICIENT_EVIDENCE" || completeness === "UNREADABLE";

            return (
              <div className="card-slate p-6 sm:p-8 bg-gradient-to-br from-slate-900 to-slate-850 text-white shadow-xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-md border ${
                        isInsufficient
                          ? "bg-amber-950 text-amber-400 border-amber-800"
                          : isCompliant
                            ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                            : "bg-red-950 text-red-400 border-red-800"
                      }`}>
                        {completeness}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        {coverage}
                      </span>
                    </div>

                    <h3 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                      {lastResult.classification?.product_name || "Packaged Commodity"}
                    </h3>
                    <p className="text-xs text-slate-300">
                      Evaluated against the Legal Metrology (Packaged Commodities) Rules, 2011.
                    </p>
                  </div>

                  <div className="flex items-center gap-4 bg-slate-800/80 p-4 rounded-2xl border border-slate-700 flex-shrink-0">
                    <div className="text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Compliance Index</span>
                      <p className={`text-4xl font-black ${
                        !isAssessable
                          ? "text-amber-400"
                          : isCompliant
                            ? "text-emerald-400"
                            : "text-red-400"
                      }`}>
                        {isAssessable ? score : "N/A"}{isAssessable && <span className="text-xl text-slate-400">/100</span>}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          <div className="card-slate p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
              <div>
                <h3 className="text-base font-extrabold text-slate-900 tracking-tight">
                  8 Mandatory Legal Metrology Declarations
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Statutory evaluation based strictly on user-uploaded package image evidence
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOcrDrawerOpen(true)}
                className="text-xs font-bold text-slate-600 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl hover:bg-slate-50"
              >
                📄 Raw OCR Inspector
              </button>
            </div>

            {/* Verified from Your Package */}
            {(() => {
              const passedFields = (lastResult.compliance?.fields || []).filter(f => f.status === "pass");
              if (passedFields.length === 0) return null;

              return (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <h4 className="text-xs font-black text-emerald-900 uppercase tracking-wide">
                      Verified from Your Package ({passedFields.length})
                    </h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {passedFields.map((field, idx) => (
                      <div
                        key={idx}
                        onClick={() => setActiveRuleDrawer(field)}
                        className="p-3.5 rounded-xl border border-emerald-200/80 bg-emerald-50/30 hover:bg-emerald-50/60 transition-all cursor-pointer flex items-start justify-between gap-3 shadow-2xs"
                      >
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                              {field.severity || "Critical"}
                            </span>
                            <h5 className="text-xs font-bold text-slate-900 truncate">{field.field_name}</h5>
                          </div>
                          <p className="text-xs text-slate-700 truncate font-mono">
                            "{field.extracted_value}"
                          </p>
                        </div>
                        <span className="text-[10px] font-extrabold uppercase px-2 py-1 rounded-md flex-shrink-0 badge-compliant">
                          Confirmed
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* Not Found in Uploaded Images */}
            {(() => {
              const missingFields = (lastResult.compliance?.fields || []).filter(f => f.status !== "pass");
              if (missingFields.length === 0) return null;

              return (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                    <h4 className="text-xs font-black text-red-900 uppercase tracking-wide">
                      Not Found in Uploaded Images ({missingFields.length})
                    </h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {missingFields.map((field, idx) => {
                      const isUnreadable = field.evidence_status === "UNREADABLE";
                      return (
                        <div
                          key={idx}
                          onClick={() => setActiveRuleDrawer(field)}
                          className="p-3.5 rounded-xl border border-red-200/80 bg-red-50/30 hover:bg-red-50/60 transition-all cursor-pointer flex items-start justify-between gap-3 shadow-2xs"
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                field.severity === "Critical" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
                              }`}>
                                {field.severity || "Rule"}
                              </span>
                              <h5 className="text-xs font-bold text-slate-900 truncate">{field.field_name}</h5>
                            </div>
                            <p className="text-xs text-red-700 truncate font-mono">
                              {isUnreadable ? "Text unreadable on image" : "Not declared on uploaded panel"}
                            </p>
                          </div>
                          <span className={`text-[10px] font-extrabold uppercase px-2 py-1 rounded-md flex-shrink-0 ${
                            isUnreadable ? "badge-unreadable" : "badge-violation"
                          }`}>
                            {isUnreadable ? "Unreadable" : "Missing"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Supplementary Groq AI Analysis & Recommendations */}
          {lastResult.ai_analysis && (
            <div className="card-slate p-6 space-y-4 border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm shadow-xs">
                    🤖
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-extrabold text-slate-900 tracking-tight">
                        Groq AI Semantic Insights & Recommendations
                      </h3>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-extrabold bg-purple-50 text-purple-700 border border-purple-200">
                        {lastResult.ai_analysis.model || "Groq LLM"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Supplementary AI intelligence for entity normalization & packaging fix guidance.
                    </p>
                  </div>
                </div>
              </div>

              {lastResult.ai_analysis.available ? (
                <div className="space-y-4 pt-1">
                  {lastResult.ai_analysis.explanation && (
                    <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-100 text-xs text-purple-950 leading-relaxed">
                      <strong className="font-bold text-purple-900 block mb-1">AI Package Summary:</strong>
                      {lastResult.ai_analysis.explanation}
                    </div>
                  )}

                  {/* Normalized Entities */}
                  {lastResult.ai_analysis.normalized_entities && Object.keys(lastResult.ai_analysis.normalized_entities).length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">
                        AI Normalized Declarations
                      </h4>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                        {Object.entries(lastResult.ai_analysis.normalized_entities).map(([k, v]) => (
                          <div key={k} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block truncate">
                              {k.replace(/_/g, " ")}
                            </span>
                            <span className="font-semibold text-slate-800 truncate block mt-0.5" title={v || "Not found"}>
                              {v || <span className="text-slate-400 italic">Not found</span>}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  {lastResult.ai_analysis.recommendations && lastResult.ai_analysis.recommendations.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">
                        Actionable Compliance Recommendations
                      </h4>
                      <ul className="space-y-1.5">
                        {lastResult.ai_analysis.recommendations.map((rec, rIdx) => (
                          <li key={rIdx} className="flex items-start gap-2 text-xs text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            <span className="text-emerald-600 font-bold">💡</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Semantic Observations */}
                  {lastResult.ai_analysis.semantic_observations && lastResult.ai_analysis.semantic_observations.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">
                        Semantic Observations
                      </h4>
                      <ul className="space-y-1.5">
                        {lastResult.ai_analysis.semantic_observations.map((obs, oIdx) => (
                          <li key={oIdx} className="flex items-start gap-2 text-xs text-slate-600 bg-white p-2 rounded-lg border border-slate-200">
                            <span className="text-slate-400">•</span>
                            <span>{obs}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                  <span>ℹ️</span>
                  <p>
                    {lastResult.ai_analysis.message ||
                      "AI analysis temporarily unavailable — Statutory compliance decision completed using deterministic Legal Metrology rules."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* AI-Assisted Supplementary Product Research & Missing Panel Recovery */}
          {lastResult.external_research && lastResult.external_research.status === "success" && (
            <div className="card-slate p-6 space-y-5 border-sky-200 bg-gradient-to-b from-sky-50/30 to-white">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/80 pb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-bold text-sm shadow-xs">
                    🌐
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-extrabold text-slate-900 tracking-tight">
                        AI-Assisted Supplementary Product Research
                      </h3>
                      {lastResult.external_research.product_match?.confidence && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${
                          lastResult.external_research.product_match.confidence === "high_confidence"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                            : lastResult.external_research.product_match.confidence === "medium_confidence"
                            ? "bg-amber-50 text-amber-700 border-amber-300"
                            : "bg-slate-100 text-slate-600 border-slate-300"
                        }`}>
                          {String(lastResult.external_research.product_match.confidence).replace("_", " ")} ({Math.round((lastResult.external_research.product_match.confidence_score || lastResult.external_research.product_match.confidence || 0) * 100)}%)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Matched: <strong className="text-slate-800 font-bold">{lastResult.external_research.product_match?.brand} {lastResult.external_research.product_match?.name || lastResult.external_research.product_match?.matched_product}</strong>
                      {lastResult.external_research.product_match?.matched_by && (
                        <span className="text-[10px] text-slate-400 ml-1.5 font-mono">
                          [via {lastResult.external_research.product_match.matched_by}]
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                {lastResult.external_research.sources && lastResult.external_research.sources.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {lastResult.external_research.sources.map((src, sIdx) => (
                      <a
                        key={sIdx}
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] font-bold text-sky-700 hover:text-sky-900 bg-sky-50 border border-sky-200 px-2.5 py-1 rounded-lg hover:bg-sky-100 transition-colors inline-flex items-center gap-1"
                      >
                        <span>🔗</span>
                        <span>{src.name}</span>
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {/* Identity Conflicts Alert (If External Catalog Differs from Package Evidence) */}
              {lastResult.external_research.identity_conflicts && lastResult.external_research.identity_conflicts.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs space-y-1.5">
                  <div className="flex items-center gap-2 font-black text-amber-950">
                    <span className="text-base">⚠️</span>
                    <span>Potential Product Identity Conflict Detected</span>
                  </div>
                  {lastResult.external_research.identity_conflicts.map((conf, cIdx) => (
                    <div key={cIdx} className="text-[11px] leading-relaxed pl-6 space-y-0.5">
                      <p>
                        <strong>Package Evidence:</strong> <span className="font-mono">{conf.package_value}</span> vs{" "}
                        <strong>External Catalog:</strong> <span className="font-mono">{conf.external_value}</span>
                      </p>
                      <p className="text-amber-800">{conf.recommendation}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Recovered Reference Declarations vs Package Evidence */}
              {(() => {
                const fields = lastResult.external_research.external_reference_fields || lastResult.external_research.fields || [];
                if (fields.length === 0) return null;

                return (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                        Missing Package Declarations & External Catalog References
                      </h4>
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                        REQUIRES PACKAGE VERIFICATION
                      </span>
                    </div>

                    <div className="space-y-2">
                      {fields.map((field, fIdx) => (
                        <div key={fIdx} className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-2">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                            <span className="text-xs font-black text-slate-900">{field.field_name}</span>
                            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 self-start sm:self-auto">
                              {String(field.verification_status || "REQUIRES_PACKAGE_VERIFICATION").replace(/_/g, " ")}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                            <div className="p-2.5 rounded-lg bg-red-50/60 border border-red-200 text-red-900">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-red-700 block">Package Evidence</span>
                              <span className="font-semibold block mt-0.5">Not detected on uploaded panel</span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-sky-50/60 border border-sky-200 text-sky-950">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-700 block">External Catalog Reference</span>
                              <span className="font-bold font-mono block mt-0.5">{field.value}</span>
                            </div>
                          </div>

                          <p className="text-[11px] text-slate-500 leading-relaxed italic">
                            ℹ️ {field.explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Recommended Additional Package Photos */}
              {(() => {
                const recs = lastResult.external_research.package_verification_required || [];
                const genericRecs = lastResult.external_research.recommended_photos || [];

                return (
                  <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-2">
                    <div className="flex items-center gap-2 text-emerald-900 font-extrabold">
                      <span className="text-base">📸</span>
                      <span>Actionable Next Steps: Upload Specific Package Photos for 100% Verification</span>
                    </div>
                    <ul className="space-y-1.5 text-emerald-950 pl-5 list-disc">
                      {recs.length > 0
                        ? recs.map((reqItem, rIdx) => (
                            <li key={rIdx} className="leading-relaxed">
                              <strong>{reqItem.recommended_panel}:</strong> {reqItem.recommendation}
                            </li>
                          ))
                        : genericRecs.map((recPhoto, pIdx) => (
                            <li key={pIdx} className="leading-relaxed">
                              {recPhoto}
                            </li>
                          ))}
                    </ul>
                  </div>
                );
              })()}

              {/* Mandatory Legal Evidence Disclaimer */}
              <div className="p-3 rounded-xl bg-slate-100 border border-slate-200 text-[11px] text-slate-600 leading-relaxed">
                <strong>Legal Evidence Notice:</strong> {lastResult.external_research.disclaimer || "Internet and catalog references are supplementary assistance tools. Under the Legal Metrology (Packaged Commodities) Rules, 2011, statutory compliance is assessed solely on physical packaging declarations. External data does not alter legal scores or convert missing declarations to verified."}
              </div>
            </div>
          )}

          <div className="card-slate p-6 border-slate-200">
            <h3 className="text-sm font-extrabold text-slate-900">Report Non-Compliance Grievance</h3>
            <p className="text-xs text-slate-500 mt-1">
              Found a violation? Submit this audit record to the Legal Metrology officer review queue.
            </p>

            {reportSuccess ? (
              <div className="mt-3 p-3 bg-emerald-50 text-emerald-800 rounded-xl text-xs font-bold">
                ✓ Grievance submitted successfully for regulatory review.
              </div>
            ) : (
              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  placeholder="Optional grievance comment (e.g. Overcharging, Net quantity missing)..."
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  className="input-field text-xs flex-1"
                />
                <button
                  type="button"
                  onClick={handleReportGrievance}
                  disabled={reporting}
                  className="btn-accent whitespace-nowrap"
                >
                  {reporting ? "Submitting..." : "Report Violation"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <AppDrawer
        isOpen={ocrDrawerOpen}
        onClose={() => setOcrDrawerOpen(false)}
        title="OCR Text Inspector"
        subtitle="Complete extracted text tokens from package"
      >
        <pre className="p-4 bg-slate-900 text-slate-200 text-xs font-mono rounded-xl max-h-[70vh] overflow-y-auto whitespace-pre-wrap">
          {lastResult?.ocr?.full_text || "No OCR text extracted."}
        </pre>
      </AppDrawer>

      <AppDrawer
        isOpen={Boolean(activeRuleDrawer)}
        onClose={() => setActiveRuleDrawer(null)}
        title={activeRuleDrawer?.field_name || "Rule Details"}
        subtitle={`Severity: ${activeRuleDrawer?.severity || "Standard"}`}
      >
        {activeRuleDrawer && (
          <div className="space-y-4">
            <div className="card-slate p-4 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-600 uppercase">Verification Status</span>
              <span className={`text-xs font-extrabold px-3 py-1 rounded-lg ${
                activeRuleDrawer.status === "pass" ? "badge-compliant" : "badge-violation"
              }`}>
                {activeRuleDrawer.status === "pass" ? "VERIFIED PRESENT" : "POTENTIAL VIOLATION"}
              </span>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Extracted Value / Evidence</h4>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono">
                {activeRuleDrawer.extracted_value || "No matching value found in extracted OCR text."}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Statutory Requirement</h4>
              <p className="text-xs text-slate-600 bg-white p-3 rounded-xl border border-slate-200 leading-relaxed">
                Under the Legal Metrology (Packaged Commodities) Rules, 2011, this declaration must appear prominently on the Principal Display Panel with minimum specified font height tolerances.
              </p>
            </div>
          </div>
        )}
      </AppDrawer>
    </div>
  );
}
