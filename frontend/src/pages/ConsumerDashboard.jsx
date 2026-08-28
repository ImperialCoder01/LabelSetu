import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../lib/supabase";
import { useTranslation } from "react-i18next";
import BarcodeScanner from "../components/BarcodeScanner";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

function UnitPriceComparator() {
  const [p1, setP1] = useState({ price: "50", qty: "200", unit: "g" });
  const [p2, setP2] = useState({ price: "110", qty: "500", unit: "g" });

  const cost1 = (parseFloat(p1.price) / parseFloat(p1.qty)) || 0;
  const cost2 = (parseFloat(p2.price) / parseFloat(p2.qty)) || 0;

  const diff = cost1 && cost2 ? Math.abs(((cost1 - cost2) / Math.max(cost1, cost2)) * 100).toFixed(1) : 0;
  const winner = cost1 < cost2 ? "Option A" : cost1 > cost2 ? "Option B" : "Equal";

  return (
    <div className="card-slate">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2">
            <span>⚖️</span> Unit Sale Price Comparator (Rule 6)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Compare cost per gram/ml across pack sizes to spot misleading quantity pricing
          </p>
        </div>
        <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-accent-50 text-accent-800 border border-accent-200">
          Consumer Saver
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className={`p-4 rounded-xl border transition-all ${winner === "Option A" ? "border-accent-400 bg-accent-50/40 shadow-sm" : "border-slate-200 bg-slate-50/50"}`}>
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-xs font-bold text-slate-800">Option A (Small Pack)</span>
            {winner === "Option A" && <span className="text-[11px] font-bold text-accent-800 bg-accent-100 px-2 py-0.5 rounded border border-accent-300">Better Value ✓</span>}
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-slate-500 font-semibold mb-1 block">Price (₹)</label>
              <input type="number" placeholder="Price (₹)" value={p1.price} onChange={(e) => setP1({...p1, price: e.target.value})} className="input-field text-xs" />
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-slate-500 font-semibold mb-1 block">Quantity</label>
              <input type="number" placeholder="Qty" value={p1.qty} onChange={(e) => setP1({...p1, qty: e.target.value})} className="input-field text-xs" />
            </div>
            <div className="self-end pb-2.5">
              <span className="text-xs font-medium text-slate-500">{p1.unit}</span>
            </div>
          </div>
          <p className="text-xs font-mono font-bold text-slate-900 mt-3 pt-2 border-t border-slate-200/60">
            Unit Price: ₹{(cost1 * 100).toFixed(2)} / 100{p1.unit}
          </p>
        </div>

        <div className={`p-4 rounded-xl border transition-all ${winner === "Option B" ? "border-accent-400 bg-accent-50/40 shadow-sm" : "border-slate-200 bg-slate-50/50"}`}>
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-xs font-bold text-slate-800">Option B (Large Pack)</span>
            {winner === "Option B" && <span className="text-[11px] font-bold text-accent-800 bg-accent-100 px-2 py-0.5 rounded border border-accent-300">Better Value ✓</span>}
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-slate-500 font-semibold mb-1 block">Price (₹)</label>
              <input type="number" placeholder="Price (₹)" value={p2.price} onChange={(e) => setP2({...p2, price: e.target.value})} className="input-field text-xs" />
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-slate-500 font-semibold mb-1 block">Quantity</label>
              <input type="number" placeholder="Qty" value={p2.qty} onChange={(e) => setP2({...p2, qty: e.target.value})} className="input-field text-xs" />
            </div>
            <div className="self-end pb-2.5">
              <span className="text-xs font-medium text-slate-500">{p2.unit}</span>
            </div>
          </div>
          <p className="text-xs font-mono font-bold text-slate-900 mt-3 pt-2 border-t border-slate-200/60">
            Unit Price: ₹{(cost2 * 100).toFixed(2)} / 100{p2.unit}
          </p>
        </div>
      </div>

      {cost1 > 0 && cost2 > 0 && (
        <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg text-xs text-sky-900 flex justify-between items-center">
          <span>
            <b>{winner}</b> is <b>{diff}% cheaper</b> per unit quantity.
          </span>
          <span className="font-mono font-bold text-sky-800 bg-sky-100 px-2 py-0.5 rounded">
            Rule 6 Verified
          </span>
        </div>
      )}
    </div>
  );
}

function UploadScreen({ onFilesSelected, selectedFiles, onRemoveFile }) {
  const { t } = useTranslation();
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);
  const cameraRef = useRef(null);

  const handleFiles = useCallback((files) => {
    if (!files || files.length === 0) return;
    const valid = Array.from(files).filter((f) => f.type.startsWith("image/"));
    onFilesSelected(valid);
  }, [onFilesSelected]);

  const handleInputChange = (e) => handleFiles(e.target.files);
  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); };

  const isMaxReached = selectedFiles.length >= 5;

  return (
    <div className="card-slate space-y-5">
      {/* Proactive Packaging Photo Guidance */}
      <div className="p-4 bg-slate-900 text-white rounded-xl shadow-sm border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <p className="font-bold text-xs uppercase tracking-wider text-accent-400 flex items-center gap-1.5">
            <span>📸</span> Packaging Photo Guidance for 100% Verification
          </p>
          <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
            Max 5 Photos
          </span>
        </div>
        <p className="text-xs text-slate-300 mb-3">
          Multiple panels of the same package are aggregated automatically without false missing penalties.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/80 text-xs">
            <span className="font-bold text-white block mb-0.5">1. Front Panel</span>
            <span className="text-[11px] text-slate-400">Brand & Commodity Name</span>
          </div>
          <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/80 text-xs">
            <span className="font-bold text-white block mb-0.5">2. Back Panel</span>
            <span className="text-[11px] text-slate-400">MRP, Net Wt, Mfg Date</span>
          </div>
          <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/80 text-xs">
            <span className="font-bold text-white block mb-0.5">3. Side Panel</span>
            <span className="text-[11px] text-slate-400">Consumer Care & Address</span>
          </div>
          <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/80 text-xs">
            <span className="font-bold text-white block mb-0.5">4. Base / Flap</span>
            <span className="text-[11px] text-slate-400">Batch No & Expiry</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900">Upload Product Packaging Photo(s)</h2>
          <p className="text-xs text-slate-500 mt-0.5">Select 1 or multiple photos of the same package</p>
        </div>
        {selectedFiles.length > 0 && (
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-accent-50 text-accent-800 border border-accent-200">
            {selectedFiles.length} / 5 Selected
          </span>
        )}
      </div>

      {/* Selected File Previews */}
      {selectedFiles.length > 0 ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {selectedFiles.map((file, idx) => (
              <div key={idx} className="relative group rounded-xl border border-slate-200 bg-slate-50 p-2 text-center overflow-hidden">
                <div className="w-full h-24 bg-slate-200 rounded-lg overflow-hidden flex items-center justify-center mb-1.5">
                  <img
                    src={URL.createObjectURL(file)}
                    alt={`Preview ${idx + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="text-[10px] font-mono font-bold text-slate-800 truncate px-1">{file.name}</div>
                <div className="text-[9px] font-mono text-slate-500">{(file.size / 1024).toFixed(0)} KB</div>
                <span className="absolute top-3 left-3 bg-slate-900/80 text-white text-[9px] font-bold px-1.5 py-0.5 rounded">
                  #{idx + 1}
                </span>
                <button
                  type="button"
                  onClick={() => onRemoveFile(idx)}
                  className="absolute top-3 right-3 bg-red-600 hover:bg-red-700 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs shadow-md transition-colors"
                  title="Remove photo"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>

          {!isMaxReached && (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="w-full py-2.5 border border-dashed border-slate-300 hover:border-slate-400 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors flex items-center justify-center gap-1.5"
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
          className={"border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all " + (dragOver ? "border-accent-500 bg-accent-50/50" : "border-slate-300 hover:border-slate-400 hover:bg-slate-50/50")}
        >
          <div className="mx-auto mb-3 w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shadow-sm">
            <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" />
            </svg>
          </div>
          <p className="text-sm font-bold text-slate-900">Click or Drag & Drop Product Packaging Photo(s)</p>
          <p className="text-xs text-slate-500 mt-1">Supports PNG, JPEG, WebP (Max 10MB per file, Max 5 files)</p>
        </div>
      )}

      <input ref={fileRef} type="file" accept="image/*" multiple onChange={handleInputChange} className="hidden" id="file-upload" />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={handleInputChange} className="hidden" id="camera-capture" />

      <div className="flex gap-3 pt-1">
        <label htmlFor="camera-capture" className="btn-secondary flex-1 cursor-pointer">
          <span>📷</span> Take Photo
        </label>
        <label htmlFor="file-upload" className="btn-secondary flex-1 cursor-pointer">
          <span>📁</span> {t("consumer.browseFiles")}
        </label>
      </div>
    </div>
  );
}

function ProcessingScreen() {
  const steps = [
    { label: "Validating Image Magic Bytes & Content Type...", icon: "🛡️" },
    { label: "Applying OpenCV Enhancement & Quality Analysis...", icon: "🔍" },
    { label: "Running OCR Text Extraction Engine...", icon: "📄" },
    { label: "Classifying Package Panels & Declarations...", icon: "📦" },
    { label: "Verifying Same-Package Identity across Photos...", icon: "🆔" },
    { label: "Aggregating Multi-Image Evidence & Resolving Conflicts...", icon: "⚖️" },
    { label: "Computing Legal Metrology Compliance Score...", icon: "✨" },
  ];

  return (
    <div className="card-slate flex flex-col items-center py-12 text-center">
      <div className="relative w-16 h-16 mb-6">
        <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
        <div className="absolute inset-0 rounded-full border-4 border-slate-900 border-t-transparent animate-spin" />
      </div>
      <h3 className="text-lg font-bold text-slate-900 mb-1">Analyzing Packaging Evidence</h3>
      <p className="text-xs text-slate-500 mb-5">Running multi-stage Legal Metrology verification pipeline...</p>

      <div className="space-y-3 w-full max-w-sm text-left">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 animate-pulse" style={{ animationDelay: (i * 200) + "ms" }}>
            <span className="text-sm">{step.icon}</span>
            <span className="font-medium">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarcodeLookupPanel({ barcodeData, mismatch }) {
  if (!barcodeData) return null;
  if (!barcodeData.found) {
    return (
      <div className="card-slate">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide mb-2">Barcode Catalog Lookup</h3>
        <p className="text-xs text-slate-500">Barcode <span className="font-mono font-bold text-slate-700">{barcodeData.barcode}</span> was not found in Open Food Facts catalog.</p>
      </div>
    );
  }
  return (
    <div className="card-slate space-y-3 border-sky-200 bg-sky-50/30">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
          <span>🏷️</span> Barcode Catalog Cross-Reference
        </h3>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-100 text-sky-900 border border-sky-300">
          Provenance: BARCODE_CATALOG
        </span>
      </div>
      <p className="text-xs text-slate-600">
        Catalog metadata is kept separate and does NOT satisfy image declarations without photo evidence.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono bg-white p-3 rounded-lg border border-slate-200">
        <div><span className="text-slate-400 block text-[10px]">PRODUCT</span><span className="font-bold text-slate-900">{barcodeData.product_name || "N/A"}</span></div>
        <div><span className="text-slate-400 block text-[10px]">BRAND</span><span className="font-bold text-slate-900">{barcodeData.brand || "N/A"}</span></div>
        <div><span className="text-slate-400 block text-[10px]">ORIGIN</span><span className="font-bold text-slate-900">{barcodeData.origins || "N/A"}</span></div>
        <div><span className="text-slate-400 block text-[10px]">QUANTITY</span><span className="font-bold text-slate-900">{barcodeData.quantity || "N/A"}</span></div>
      </div>
    </div>
  );
}

function ResultsScreen({ report, onScanAgain }) {
  const { t } = useTranslation();
  const [showNormalizedOcr, setShowNormalizedOcr] = useState(true);

  if (!report) return null;

  const compliance = report.compliance || {};
  const ocr = report.ocr || {};
  const barcode_lookup = report.barcode_lookup;
  const manufacturer_mismatch = report.manufacturer_mismatch;
  const duplicate_count = compliance.duplicate_count || 0;

  const score = compliance.overall_score !== undefined && compliance.overall_score !== null ? compliance.overall_score : null;
  const completeness = compliance.verification_completeness || "NO_CONFIRMED_VIOLATION";
  const isAssessable = score !== null;

  let scoreColor = "text-slate-900";
  let scoreStroke = "#10b981"; // Emerald
  let scoreBg = "bg-accent-50 text-accent-900 border-accent-200";

  if (!isAssessable) {
    scoreColor = "text-amber-700";
    scoreStroke = "#d97706";
    scoreBg = "bg-amber-50 text-amber-900 border-amber-200";
  } else if (score >= 80) {
    scoreColor = "text-accent-700";
    scoreStroke = "#059669";
    scoreBg = "bg-accent-50 text-accent-900 border-accent-200";
  } else if (score >= 50) {
    scoreColor = "text-amber-700";
    scoreStroke = "#d97706";
    scoreBg = "bg-amber-50 text-amber-900 border-amber-200";
  } else {
    scoreColor = "text-red-700";
    scoreStroke = "#dc2626";
    scoreBg = "bg-red-50 text-red-900 border-red-200";
  }

  const dashLen = 326.72;
  const dashOff = isAssessable ? dashLen - (dashLen * score) / 100 : dashLen;

  let completenessBadge = "Verification Pending";
  let completenessDesc = "Additional photos may be required for full verification.";
  let badgeStyle = "bg-slate-100 text-slate-800 border-slate-300";

  if (completeness === "FULLY_VERIFIED") {
    completenessBadge = "Fully Verified ✓";
    completenessDesc = "All mandatory Legal Metrology declarations have been verified across uploaded photos.";
    badgeStyle = "bg-accent-100 text-accent-900 border-accent-300";
  } else if (completeness === "NO_CONFIRMED_VIOLATION") {
    completenessBadge = "No Confirmed Violations Observed";
    completenessDesc = "No confirmed legal violations were found in the uploaded photos, but additional panels are required for 100% verification.";
    badgeStyle = "bg-sky-100 text-sky-900 border-sky-300";
  } else if (completeness === "CONFIRMED_NON_COMPLIANCE") {
    completenessBadge = "Confirmed Legal Violation(s)";
    completenessDesc = "One or more mandatory declarations are physically missing from readable declaration panels.";
    badgeStyle = "bg-red-100 text-red-900 border-red-300";
  } else if (completeness === "UNREADABLE") {
    completenessBadge = "Image Quality Unreadable";
    completenessDesc = "Packaging photo quality is unreadable. Retake photo with steady focus and clear lighting.";
    badgeStyle = "bg-amber-100 text-amber-900 border-amber-300";
  } else if (completeness === "SCREENSHOT") {
    completenessBadge = "Non-Product UI Screenshot";
    completenessDesc = "The uploaded file appears to be a digital screenshot rather than physical product packaging.";
    badgeStyle = "bg-slate-200 text-slate-900 border-slate-400";
  }

  return (
    <div className="space-y-6">
      {/* Package Identity Mismatch Alert */}
      {compliance.package_identity && !compliance.package_identity.match && (
        <div className="p-4 bg-orange-50 border-2 border-orange-300 rounded-xl flex items-start gap-3 shadow-sm">
          <span className="text-2xl">🚫</span>
          <div>
            <h3 className="text-base font-bold text-orange-900">Package Identity Mismatch</h3>
            <p className="text-xs text-orange-800 mt-1">{compliance.package_identity.detail}</p>
          </div>
        </div>
      )}

      {/* Duplicate Uploads Alert */}
      {duplicate_count > 0 && (
        <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-900 flex items-center gap-2">
          <span>ℹ️</span>
          <span><b>{duplicate_count}</b> duplicate image upload(s) detected and safely deduplicated.</span>
        </div>
      )}

      {/* Verification Completeness & Evidence Coverage Card */}
      <div className="card-slate border-slate-300 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-3 border-b border-slate-100">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-800 border border-slate-300">
            Evidence Coverage: {compliance.evidence_coverage || `${compliance.passed}/${compliance.total_fields} assessable`}
          </span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${badgeStyle}`}>
            Verification: {completenessBadge}
          </span>
        </div>

        <p className="text-xs text-slate-700 font-medium">{completenessDesc}</p>

        {compliance.actions_required && compliance.actions_required.length > 0 && (
          <div className="mt-3 p-3 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-900">
            <span className="font-bold block mb-1">Required Actions:</span>
            <ul className="list-disc pl-4 space-y-1">
              {compliance.actions_required.map((act, i) => (
                <li key={i}>{act}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Score Gauge Card */}
      <div className="card-slate flex flex-col items-center pt-8 pb-6">
        <div className="relative w-32 h-32 mb-3">
          <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#f1f5f9" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={dashLen}
              strokeDashoffset={dashOff}
              style={{ stroke: scoreStroke }}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-extrabold font-mono ${scoreColor}`}>{isAssessable ? score : "N/A"}</span>
            {isAssessable && <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">/ 100</span>}
          </div>
        </div>

        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${scoreBg}`}>
          {!isAssessable ? "Insufficient Evidence" : score >= 80 ? "Compliant" : score >= 50 ? "Partially Verified" : "Non-Compliant"}
        </span>

        <p className="text-xs text-slate-500 mt-2 text-center max-w-sm">
          {!isAssessable
            ? "Compliance Index is N/A because 0 declarations could be assessed from the uploaded photos."
            : score === 100 && compliance.passed < compliance.total_fields
            ? "100/100 — No confirmed violations found in photographed panels."
            : `Passed Declarations: ${compliance.passed}/${compliance.total_fields}`}
        </p>
      </div>

      {/* Multi-Image Granular Evidence Checklist */}
      <div className="card-slate">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2">
            <span>📊</span> Multi-Image Legal Metrology Evidence
          </h3>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-300">
            Provenanced Engine
          </span>
        </div>

        <div className="space-y-3">
          {compliance.fields && compliance.fields.map((field) => {
            const evStatus = field.evidence_status || (field.status === "pass" ? "CONFIRMED_PRESENT" : "CONFIRMED_MISSING");
            
            let badgeClass = "badge-present";
            let icon = "✓";
            if (evStatus === "CONFIRMED_MISSING") { badgeClass = "badge-missing"; icon = "✗"; }
            else if (evStatus === "NOT_VISIBLE") { badgeClass = "badge-not-visible"; icon = "○"; }
            else if (evStatus === "UNREADABLE") { badgeClass = "badge-unreadable"; icon = "!"; }
            else if (evStatus === "NOT_DETECTED") { badgeClass = "badge-not-detected"; icon = "?"; }
            else if (evStatus === "CONFLICTING_EVIDENCE") { badgeClass = "badge-conflicting"; icon = "⚡"; }

            const provSource = field.source || "IMAGE";

            return (
              <div key={field.field_id} className={`p-4 rounded-xl border transition-all ${evStatus === "CONFIRMED_PRESENT" ? "bg-accent-50/30 border-accent-200" : evStatus === "CONFIRMED_MISSING" ? "bg-red-50/40 border-red-200" : "bg-slate-50/70 border-slate-200"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-sm font-bold text-slate-900">{field.field_name}</span>
                      <span className={`text-[10px] font-bold ${field.severity === "Critical" ? "bg-red-100 text-red-800 border border-red-200" : "bg-slate-200 text-slate-700"} px-1.5 py-0.5 rounded`}>
                        {field.severity}
                      </span>
                      <span className={badgeClass}>
                        {icon} {evStatus}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-md font-bold bg-slate-200 text-slate-800 border border-slate-300">
                        Provenance: {provSource}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 mt-1">{field.reason || field.description}</p>

                    {field.action && (
                      <p className="text-xs text-sky-900 mt-1.5 font-medium bg-sky-50 p-2 rounded-lg border border-sky-200">
                        💡 <span className="font-bold">Guidance:</span> {field.action}
                      </p>
                    )}

                    {field.extracted_value && (
                      <div className="mt-2">
                        <span className="text-[10px] font-bold text-slate-400 block mb-0.5">EXTRACTED VALUE</span>
                        <div className="ocr-code-block font-mono font-bold text-accent-900 bg-accent-50/80 border-accent-200 inline-block px-3 py-1">
                          {field.extracted_value}
                        </div>
                      </div>
                    )}
                  </div>

                  {field.score_impact !== 0 && (
                    <span className="text-xs font-mono font-bold text-red-700 bg-red-100 px-2.5 py-1 rounded-md border border-red-200 whitespace-nowrap">
                      {field.score_impact} pts
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {manufacturer_mismatch && !manufacturer_mismatch.match && (
        <div className="p-4 bg-red-50 border-2 border-red-300 rounded-xl flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="text-base font-bold text-red-800">{t("consumer.manufacturerMismatch")}</h3>
            <p className="text-xs text-red-700 mt-1">{manufacturer_mismatch.mismatch_detail}</p>
            <p className="text-xs text-red-600 mt-2 font-mono">{t("consumer.registeredBrand")} <b>{manufacturer_mismatch.off_brand}</b></p>
          </div>
        </div>
      )}

      <BarcodeLookupPanel barcodeData={barcode_lookup} mismatch={manufacturer_mismatch} />

      {/* Raw vs Domain-Normalized OCR Inspector */}
      {ocr?.full_text && (
        <div className="card-slate">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
              <span>🔍</span> OCR Engine Text Extraction Inspector
            </h3>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setShowNormalizedOcr(false)}
                className={`text-xs px-2.5 py-1 rounded-md font-bold transition-all ${!showNormalizedOcr ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                Raw OCR
              </button>
              <button
                type="button"
                onClick={() => setShowNormalizedOcr(true)}
                className={`text-xs px-2.5 py-1 rounded-md font-bold transition-all ${showNormalizedOcr ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                Normalized OCR
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-500 mb-2">
            {showNormalizedOcr
              ? "Domain-Normalized OCR applies conservative Legal Metrology packaging corrections (e.g. MOP → MRP) without mutating raw OCR."
              : "Raw OCR Text contains unmodified characters extracted directly from image pixels."}
          </p>

          <pre className="ocr-code-block whitespace-pre-wrap max-h-48 overflow-y-auto">
            {showNormalizedOcr ? (ocr.normalized_full_text || ocr.full_text) : ocr.full_text}
          </pre>
        </div>
      )}

      <button type="button" onClick={onScanAgain} className="btn-primary w-full py-3 text-sm">
        {t("consumer.scanAnother")}
      </button>
    </div>
  );
}

export default function ConsumerDashboard() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [scans, setScans] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [screen, setScreen] = useState("upload");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [capturedBarcode, setCapturedBarcode] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [selectedScan, setSelectedScan] = useState(null);
  const [reportingId, setReportingId] = useState(null);
  const [reportReason, setReportReason] = useState("");
  const [reportSuccess, setReportSuccess] = useState(null);
  const [reportError, setReportError] = useState(null);

  useEffect(() => { fetchScans(); }, []);

  async function fetchScans() {
    if (!user) return;
    const { data, error } = await supabase.from("scans").select("*").eq("user_id", user.id).order("created_at", { ascending: false });
    if (!error) setScans(data || []);
    setHistoryLoading(false);
  }

  function handleFilesSelected(newFiles) {
    setSelectedFiles((prev) => {
      const combined = [...prev, ...newFiles];
      return combined.slice(0, 5); // Enforce max 5 photos
    });
  }

  function handleRemoveFile(idx) {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  }

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

  async function handleScan() {
    if (selectedFiles.length === 0 && !capturedBarcode) return;
    setScreen("processing");
    setScanError(null);
    setLastResult(null);

    const totalRawSizeKB = Math.round(
      selectedFiles.reduce((acc, f) => acc + (f.size || 0), 0) / 1024
    );

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.access_token) {
        throw new Error("Authentication session missing. Please sign in again.");
      }

      // Optional connectivity pre-check (resilient, non-blocking)
      try {
        const pingCtrl = new AbortController();
        const pingTimer = setTimeout(() => pingCtrl.abort(), 5000);
        await fetch(`${API_BASE}/health`, { signal: pingCtrl.signal });
        clearTimeout(pingTimer);
      } catch (_) {
        // Non-fatal — proceed with scan request
      }

      // Pre-scale high-res smartphone camera photos (e.g. 12MP/48MP) to standard 1600px
      // to eliminate multi-megabyte mobile upload delays and server memory spikes.
      const filesToUpload = await Promise.all(
        selectedFiles.map((file) => optimizeImageForUpload(file))
      );

      const formData = new FormData();
      filesToUpload.forEach((file) => {
        formData.append("files", file);
      });
      if (capturedBarcode) formData.append("barcode", capturedBarcode);

      const scanCtrl = new AbortController();
      const SCAN_TIMEOUT_MS = 60_000; // 60 seconds
      const scanTimer = setTimeout(() => scanCtrl.abort(), SCAN_TIMEOUT_MS);

      let res;
      try {
        res = await fetch(`${API_BASE}/api/scans/scan`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
          body: formData,
          signal: scanCtrl.signal,
        });
      } catch (netErr) {
        clearTimeout(scanTimer);
        console.error("Scan fetch network/CORS error:", netErr);
        const isAbort = netErr && netErr.name === "AbortError";
        const customErr = new Error(
          isAbort
            ? "Scan request timed out after 60 seconds. Please check your network connection and try again."
            : `Unable to reach scanning service (${netErr.message || "Network connection failed"}). Please verify your internet connection and retry.`
        );
        customErr.originalName = netErr?.name || "TypeError";
        customErr.originalMessage = netErr?.message || "Failed to fetch";
        throw customErr;
      }
      clearTimeout(scanTimer);

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const detailMsg = errBody.detail || errBody.message;
        if (res.status === 401) throw new Error("Authentication failed — please sign out and sign back in.");
        if (res.status === 403) throw new Error(`Permission denied: ${detailMsg || "Your account role does not allow scanning."}`);
        if (res.status === 404) throw new Error("Scan API endpoint not found (404).");
        if (res.status === 413) throw new Error(`Image too large: ${detailMsg || "Maximum 10 MB per image."}`);
        if (res.status === 400) throw new Error(`Invalid scan request: ${detailMsg || "Bad request."}`);
        if (res.status === 500) throw new Error(`Server processing error: ${detailMsg || "Internal server error."}`);
        if (res.status === 502 || res.status === 503 || res.status === 504) {
          throw new Error("Scanning server temporarily unavailable (gateway error). Please retry in a moment.");
        }
        throw new Error(`Scan failed (HTTP ${res.status}): ${detailMsg || res.statusText}`);
      }

      const result = await res.json();
      setLastResult(result);
      setSelectedFiles([]);
      setCapturedBarcode("");
      setScreen("results");
      fetchScans();
    } catch (err) {
      console.error("[LabelSetu Scan Diagnostic]", {
        apiHost: API_BASE,
        endpoint: `${API_BASE}/api/scans/scan`,
        errorName: err.originalName || err.name,
        errorMessage: err.originalMessage || err.message,
        online: typeof navigator !== "undefined" ? navigator.onLine : true,
        imageCount: selectedFiles.length,
        totalSizeKB: totalRawSizeKB,
      });
      setScanError({
        message: err.message,
        diagnostic: {
          apiHost: API_BASE,
          endpoint: "POST /api/scans/scan",
          online: typeof navigator !== "undefined" ? navigator.onLine : true,
          errorName: err.originalName || err.name,
          imagesCount: selectedFiles.length,
          totalSizeKB: totalRawSizeKB,
        },
      });
      setScreen("upload");
    }
  }

  async function handleReport(scanId) {
    if (!reportReason.trim()) return;
    setReportingId(scanId);
    setReportError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_BASE}/api/reports/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + session.access_token,
        },
        body: JSON.stringify({ scan_id: scanId, reason: reportReason }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || "Failed to submit report");
      }
      setReportSuccess(scanId);
      setReportReason("");
    } catch (err) {
      setReportError(err.message);
    } finally {
      setReportingId(null);
    }
  }

  function parseMissingFields(mf) {
    if (!mf) return [];
    const raw = typeof mf === "string" ? JSON.parse(mf) : mf;
    return Array.isArray(raw) ? raw : [];
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">{t("consumer.title")}</h1>
        <p className="text-xs text-slate-500 mt-1">{t("consumer.subtitle")}</p>
      </div>

      {screen === "upload" && (
        <>
          <UploadScreen onFilesSelected={handleFilesSelected} selectedFiles={selectedFiles} onRemoveFile={handleRemoveFile} />
          
          <div className="card-slate">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">Barcode Lookup</h3>
                <p className="text-xs text-slate-500 mt-0.5">Scan barcode to cross-reference Open Food Facts database</p>
              </div>
              <button
                type="button"
                onClick={() => setScreen("barcode")}
                className="btn-secondary text-xs"
              >
                {t("consumer.scanBarcode")}
              </button>
            </div>
            {capturedBarcode && (
              <div className="mt-3 p-2.5 bg-accent-50 rounded-lg flex items-center justify-between border border-accent-200 text-xs">
                <span className="text-accent-900 font-mono font-bold">Barcode: {capturedBarcode}</span>
                <button type="button" onClick={() => setCapturedBarcode("")} className="text-accent-700 hover:text-accent-900 font-bold">Clear</button>
              </div>
            )}
          </div>

          {scanError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-red-600 font-bold text-sm">⚠️</span>
                <div className="flex-1">
                  <p className="font-bold text-red-900">{typeof scanError === "object" ? scanError.message : scanError}</p>
                  {typeof scanError === "object" && scanError.diagnostic && (
                    <details className="mt-2 text-[11px] text-slate-600 cursor-pointer">
                      <summary className="font-semibold text-red-800 hover:underline">Technical Diagnostics</summary>
                      <div className="mt-1.5 p-2 bg-white rounded border border-slate-200 font-mono text-[10px] space-y-1">
                        <div><span className="text-slate-400">API Host:</span> {scanError.diagnostic.apiHost}</div>
                        <div><span className="text-slate-400">Request:</span> {scanError.diagnostic.endpoint}</div>
                        <div><span className="text-slate-400">Online:</span> {scanError.diagnostic.online ? "Yes" : "No"}</div>
                        {scanError.diagnostic.errorName && <div><span className="text-slate-400">Type:</span> {scanError.diagnostic.errorName}</div>}
                        {scanError.diagnostic.imagesCount !== undefined && <div><span className="text-slate-400">Images:</span> {scanError.diagnostic.imagesCount} ({scanError.diagnostic.totalSizeKB} KB)</div>}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={handleScan}
            disabled={selectedFiles.length === 0 && !capturedBarcode}
            className="btn-accent w-full py-3.5 text-sm"
          >
            {capturedBarcode ? (selectedFiles.length > 0 ? `Scan ${selectedFiles.length} Packaging Photo(s) & Cross-Check Barcode` : "Lookup Barcode " + capturedBarcode) : (selectedFiles.length > 1 ? `Scan ${selectedFiles.length} Packaging Photos` : t("consumer.scanLabelBtn"))}
          </button>
        </>
      )}

      {screen === "barcode" && <BarcodeScanner onDetected={(code) => { setCapturedBarcode(code); setScreen("upload"); }} onCancel={() => setScreen("upload")} onError={(msg) => { setScanError({ message: msg }); setScreen("upload"); }} />}
      {screen === "processing" && <ProcessingScreen />}
      {screen === "results" && <ResultsScreen report={lastResult} onScanAgain={() => { setLastResult(null); setScreen("upload"); }} />}

      {/* History Scans Card */}
      <div className="card-slate">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-4 pb-2 border-b border-slate-100">{t("consumer.myScans")}</h2>
        {historyLoading ? <p className="text-xs text-slate-500">{t("common.loading")}</p> : scans.length === 0 ? <p className="text-xs text-slate-500">{t("consumer.noScans")}</p> : (
          <div className="space-y-2.5">
            {scans.map((scan) => (
              <div key={scan.id} onClick={() => setSelectedScan(selectedScan?.id === scan.id ? null : scan)} className={"p-3.5 rounded-xl cursor-pointer transition-all border " + (selectedScan?.id === scan.id ? "bg-slate-100/80 border-slate-400" : "bg-slate-50 border-slate-200/70 hover:bg-slate-100/50")}>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 pr-3">
                    <p className="text-xs font-semibold text-slate-900 truncate">{scan.extracted_text?.substring(0, 80) || "No text"}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">{new Date(scan.created_at).toLocaleString()}</p>
                  </div>
                  <span className={"px-2.5 py-0.5 rounded-md text-xs font-mono font-bold border " + (scan.compliance_score >= 80 ? "bg-accent-50 text-accent-800 border-accent-200" : scan.compliance_score >= 50 ? "bg-amber-50 text-amber-800 border-amber-200" : "bg-red-50 text-red-800 border-red-200")}>{scan.compliance_score}%</span>
                </div>
                {selectedScan?.id === scan.id && (
                  <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-2" onClick={(e) => e.stopPropagation()}>
                    {scan.extracted_text && <pre className="ocr-code-block max-h-24 overflow-y-auto">{scan.extracted_text}</pre>}
                    {(() => {
                      const m = parseMissingFields(scan.missing_fields);
                      if (m.length === 0) return <p className="text-xs text-accent-700 font-bold">All mandatory fields present</p>;
                      return <div><p className="text-[11px] font-bold text-red-700 mb-1">Missing Declarations:</p><div className="flex flex-wrap gap-1">{m.map((f, i) => <span key={i} className="text-[10px] font-bold bg-red-100 text-red-800 px-2 py-0.5 rounded">{f}</span>)}</div></div>;
                    })()}

                    <div className="pt-2 border-t border-slate-200">
                      {reportSuccess === scan.id ? (
                        <div className="flex items-center gap-1.5 text-xs text-accent-700 font-bold">
                          <span>✓</span> {t("consumer.reportSubmitted")}
                        </div>
                      ) : (
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              placeholder={t("consumer.reportReason")}
                              value={reportReason}
                              onChange={(e) => setReportReason(e.target.value)}
                              className="input-field text-xs flex-1 py-1.5"
                            />
                            <button
                              type="button"
                              onClick={() => handleReport(scan.id)}
                              disabled={reportingId === scan.id}
                              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors disabled:opacity-50"
                            >
                              {reportingId === scan.id ? t("consumer.reporting") : t("consumer.reportProduct")}
                            </button>
                          </div>
                          {reportError && <p className="text-xs text-red-600">{reportError}</p>}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <UnitPriceComparator />
    </div>
  );
}
