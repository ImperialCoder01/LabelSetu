import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../lib/supabase";
import { useTranslation } from "react-i18next";
import BarcodeScanner from "../components/BarcodeScanner";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function UploadScreen({ onFileSelected }) {
  const { t } = useTranslation();
  const [preview, setPreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);
  const cameraRef = useRef(null);
  const handleFile = useCallback((file) => {
    if (!file || !file.type.startsWith("image/")) return;
    onFileSelected(file);
    setPreview(URL.createObjectURL(file));
  }, [onFileSelected]);
  const handleInputChange = (e) => handleFile(e.target.files?.[0]);
  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]); };
  useEffect(() => { return () => { if (preview) URL.revokeObjectURL(preview); }; }, [preview]);
  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Scan a Product Label</h2>
      {preview ? (
        <div className="relative mb-4">
          <img src={preview} alt="Label preview" className="w-full max-h-72 object-contain rounded-lg border border-gray-200 bg-white" />
          <button onClick={() => { setPreview(null); onFileSelected(null); if (fileRef.current) fileRef.current.value = ""; }} className="absolute top-2 right-2 bg-white/90 hover:bg-white text-gray-600 hover:text-red-600 rounded-full w-8 h-8 flex items-center justify-center shadow-sm transition-colors" title="Remove">&times;</button>
        </div>
      ) : (
        <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} className={"border-2 border-dashed rounded-xl p-10 text-center transition-colors " + (dragOver ? "border-primary-500 bg-primary-50" : "border-gray-300 hover:border-gray-400")}>
          <div className="mx-auto mb-3 w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" /></svg>
          </div>
          <p className="text-gray-600 font-medium">{t("consumer.clickToUpload")}</p>
          <p className="text-sm text-gray-400 mt-1">{t("consumer.fileFormat")}</p>
        </div>
      )}
      <input ref={fileRef} type="file" accept="image/*" onChange={handleInputChange} className="hidden" id="file-upload" />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={handleInputChange} className="hidden" id="camera-capture" />
      <div className="flex gap-3 mt-4">
        <label htmlFor="camera-capture" className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 cursor-pointer transition-colors">{t("consumer.camera")}</label>
        <label htmlFor="file-upload" className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 cursor-pointer transition-colors">{t("consumer.browseFiles")}</label>
      </div>
    </div>
  );
}
function ProcessingScreen() {
  const { t } = useTranslation();
  const steps = [
    { label: t("consumer.uploadingImage"), icon: "⬇️" },
    { label: t("consumer.runningOCR"), icon: "🔍" },
    { label: t("consumer.applyingRules"), icon: "📊" },
    { label: t("consumer.computingScore"), icon: "✨" },
  ];
  return (
    <div className="card flex flex-col items-center py-12">
      <div className="relative w-20 h-20 mb-6">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
      </div>
      <p className="text-lg font-semibold text-gray-900 mb-6">{t("consumer.analyzingLabel")}</p>
      <div className="space-y-3 w-full max-w-xs">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3 text-sm text-gray-500 animate-pulse" style={{ animationDelay: (i * 400) + "ms" }}>
            <span className="text-base">{step.icon}</span>
            <span>{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarcodeLookupPanel({ barcodeData, mismatch }) {
  if (!barcodeData) return null;
  if (!barcodeData.found) {
    return (<div className="card"><h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">Barcode Lookup</h3><p className="text-sm text-gray-500">Barcode {barcodeData.barcode} not found in Open Food Facts</p></div>);
  }
  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">Barcode Lookup ({barcodeData.barcode})</h3>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        {barcodeData.product_name && <div><p className="text-gray-400 text-xs">Product Name</p><p className="font-medium text-gray-900">{barcodeData.product_name}</p></div>}
        {barcodeData.brand && <div><p className="text-gray-400 text-xs">Brand</p><p className="font-medium text-gray-900">{barcodeData.brand}</p></div>}
        {barcodeData.manufacturing_places && <div><p className="text-gray-400 text-xs">Manufacturing</p><p className="font-medium text-gray-900">{barcodeData.manufacturing_places}</p></div>}
        {barcodeData.origins && <div><p className="text-gray-400 text-xs">Origin</p><p className="font-medium text-gray-900">{barcodeData.origins}</p></div>}
        {barcodeData.countries && <div className="col-span-2"><p className="text-gray-400 text-xs">Countries</p><p className="font-medium text-gray-900">{barcodeData.countries}</p></div>}
        {barcodeData.categories && <div className="col-span-2"><p className="text-gray-400 text-xs">Categories</p><p className="font-medium text-gray-900">{barcodeData.categories}</p></div>}
        {barcodeData.ingredients_text && <div className="col-span-2"><p className="text-gray-400 text-xs">Ingredients</p><p className="text-gray-700 text-xs max-h-20 overflow-y-auto">{barcodeData.ingredients_text}</p></div>}
      </div>
      {mismatch && !mismatch.match && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm font-semibold text-red-700">Manufacturer Mismatch Detected</p>
          <p className="text-xs text-red-600 mt-1">{mismatch.mismatch_detail}</p>
        </div>
      )}
      {mismatch && mismatch.match && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">Brand "{mismatch.off_brand}" matched in OCR text</p>
        </div>
      )}
    </div>
  );
}

function ResultsScreen({ report, onScanAgain }) {
  const { t } = useTranslation();
  if (!report) return null;
  const { compliance, ocr, barcode_lookup, manufacturer_mismatch } = report;
  const score = compliance.overall_score;
  const scoreColor = score >= 80 ? "text-green-600" : score >= 50 ? "text-yellow-500" : "text-red-600";
  const scoreBg = score >= 80 ? "bg-green-50" : score >= 50 ? "bg-yellow-50" : "bg-red-50";
  const scoreLabel = score >= 80 ? "Compliant" : score >= 50 ? "Partial" : "Non-Compliant";
  const dashLen = 2 * Math.PI * 52;
  const dashOff = 2 * Math.PI * 52 * (1 - score / 100);
  return (
    <div className="space-y-6">
      <div className="card flex flex-col items-center pt-8 pb-6">
        <div className="relative w-32 h-32 mb-4">
          <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle cx="60" cy="60" r="52" fill="none" strokeWidth="8" strokeLinecap="round" strokeDasharray={dashLen} strokeDashoffset={dashOff} style={{ stroke: score >= 80 ? "#22c55e" : score >= 50 ? "#facc15" : "#ef4444" }} className="transition-all duration-1000 ease-out" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={"text-3xl font-bold " + scoreColor}>{score}</span>
            <span className="text-xs text-gray-400">/ 100</span>
          </div>
        </div>
        <span className={"px-3 py-1 rounded-full text-sm font-semibold " + scoreBg + " " + scoreColor}>{scoreLabel}</span>
        <p className="text-xs text-gray-400 mt-2">{t("consumer.fieldsDetected", { passed: compliance.passed, total: compliance.total_fields })}{ocr && <>{" "}&middot; {t("consumer.ocrConfidence", { pct: Math.round(ocr.average_confidence * 100) })}</>}</p>
      </div>
      {manufacturer_mismatch && !manufacturer_mismatch.match && (
        <div className="p-4 bg-red-50 border-2 border-red-300 rounded-xl flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div><h3 className="text-base font-bold text-red-700">{t("consumer.manufacturerMismatch")}</h3><p className="text-sm text-red-600 mt-1">{manufacturer_mismatch.mismatch_detail}</p>          <p className="text-xs text-red-500 mt-2">{t("consumer.registeredBrand")} <span className="font-mono font-semibold">{manufacturer_mismatch.off_brand}</span></p></div>
        </div>
      )}
      <BarcodeLookupPanel barcodeData={barcode_lookup} mismatch={manufacturer_mismatch} />
      {/* Radar chart */}
      {compliance.fields.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Field Compliance Radar</h3>
          <div style={{ height: 340 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={compliance.fields.map((f) => ({ field: f.field_name, value: f.status === "pass" ? 100 : 0, status: f.status }))} cx="50%" cy="50%" outerRadius="72%">
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis
                  dataKey="field"
                  tick={({ x, y, payload }) => {
                    const parts = payload.value.split(" ");
                    const lines = [];
                    for (let i = 0; i < parts.length; i += 3) lines.push(parts.slice(i, i + 3).join(" "));
                    return (
                      <text x={x} y={y} textAnchor="middle" dominantBaseline="central" className="text-[10px] fill-gray-600">
                        {lines.map((line, li) => (
                          <tspan key={li} x={x} dy={li === 0 ? 0 : 12}>{line}</tspan>
                        ))}
                      </text>
                    );
                  }}
                />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Compliance" dataKey="value" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} strokeWidth={2} />
                <Tooltip
                  formatter={(val) => [val === 100 ? "Pass ✓" : "Fail ✗", "Status"]}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      <div className="card">          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">{t("consumer.complianceChecklist")}</h3>
        <div className="space-y-3">
          {compliance.fields.map((field) => (
            <div key={field.field_id} className={"flex items-start gap-3 p-3 rounded-lg transition-colors " + (field.status === "pass" ? "bg-green-50" : "bg-red-50")}>
              <div className={"mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 " + (field.status === "pass" ? "bg-green-500 text-white" : "bg-red-500 text-white")}>
                {field.status === "pass" ? <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg> : <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{field.field_name}</span>
                  <span className={"text-xs px-1.5 py-0.5 rounded font-medium " + (field.severity === "Critical" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600")}>{field.severity}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{field.description}</p>
                {field.matched_keyword && <span className="inline-block mt-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Found: "{field.matched_keyword}"</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
      {ocr?.extracted_entities && Object.values(ocr.extracted_entities).some(Boolean) && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
              AI Detected Package Entities
            </h3>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
              Custom Model v1.0
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {ocr.extracted_entities.mrp && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
                <span className="font-semibold text-gray-500 block">MRP</span>
                <span className="font-mono text-gray-900 font-bold">{ocr.extracted_entities.mrp}</span>
              </div>
            )}
            {ocr.extracted_entities.net_quantity && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
                <span className="font-semibold text-gray-500 block">Net Quantity</span>
                <span className="font-mono text-gray-900 font-bold">{ocr.extracted_entities.net_quantity}</span>
              </div>
            )}
            {ocr.extracted_entities.mfg_date && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
                <span className="font-semibold text-gray-500 block">Mfg / Pkd Date</span>
                <span className="font-mono text-gray-900 font-bold">{ocr.extracted_entities.mfg_date}</span>
              </div>
            )}
            {ocr.extracted_entities.unit_sale_price && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
                <span className="font-semibold text-gray-500 block">Unit Sale Price</span>
                <span className="font-mono text-gray-900 font-bold">{ocr.extracted_entities.unit_sale_price}</span>
              </div>
            )}
            {ocr.extracted_entities.fssai_lic && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200 col-span-2">
                <span className="font-semibold text-gray-500 block">FSSAI License No.</span>
                <span className="font-mono text-blue-700 font-bold">{ocr.extracted_entities.fssai_lic}</span>
              </div>
            )}
            {ocr.extracted_entities.country_of_origin && (
              <div className="bg-gray-50 p-2.5 rounded border border-gray-200">
                <span className="font-semibold text-gray-500 block">Country of Origin</span>
                <span className="font-mono text-gray-900 font-bold">{ocr.extracted_entities.country_of_origin}</span>
              </div>
            )}
          </div>
        </div>
      )}
      {ocr?.full_text && (
        <div className="card"><h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">{t("consumer.extractedText")}</h3><p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 border border-gray-200 whitespace-pre-wrap max-h-40 overflow-y-auto font-mono">{ocr.full_text}</p></div>
      )}
      <button onClick={onScanAgain} className="btn-primary w-full">{t("consumer.scanAnother")}</button>
    </div>
  );
}

export default function ConsumerDashboard() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [scans, setScans] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [screen, setScreen] = useState("upload");
  const [selectedFile, setSelectedFile] = useState(null);
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
    const { data, error } = await supabase.from("scans").select("*").eq("user_id", user.id).order("created_at", { ascending: false });
    if (!error) setScans(data);
    setHistoryLoading(false);
  }

  async function handleScan() {
    if (!selectedFile) return;
    setScreen("processing");
    setScanError(null);
    setLastResult(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Not authenticated");
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (capturedBarcode) formData.append("barcode", capturedBarcode);
      const res = await fetch(API_BASE + "/api/scans/scan", { method: "POST", headers: { Authorization: "Bearer " + session.access_token }, body: formData });
      if (!res.ok) { const errBody = await res.json().catch(() => ({})); throw new Error(errBody.detail || "Scan failed (" + res.status + ")"); }
      const result = await res.json();
      setLastResult(result);
      setSelectedFile(null);
      setCapturedBarcode("");
      setScreen("results");
      await fetchScans();
    } catch (err) {
      setScanError(err.message);
      setScreen("upload");
    }
  }

  async function handleReport(scanId) {
    setReportingId(scanId);
    setReportError(null);
    setReportSuccess(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Not authenticated");
      const res = await fetch(API_BASE + "/api/reports", {
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
    <div className="space-y-8">
      <div><h1 className="text-2xl font-bold text-gray-900">{t("consumer.title")}</h1><p className="text-gray-500 mt-1">{t("consumer.subtitle")}</p></div>
      {screen === "upload" && (
        <>
          <UploadScreen onFileSelected={setSelectedFile} />
          <div className="card">
            <div className="flex items-center justify-between">
              <div><h3 className="text-sm font-semibold text-gray-900">Barcode Lookup</h3><p className="text-xs text-gray-500 mt-0.5">Scan barcode to cross-reference with Open Food Facts</p></div>
              <button onClick={() => setScreen("barcode")} className="px-4 py-2 rounded-lg bg-primary-50 text-primary-700 text-sm font-medium hover:bg-primary-100 transition-colors">{t("consumer.scanBarcode")}</button>
            </div>
            {capturedBarcode && (<div className="mt-3 p-2 bg-green-50 rounded-lg flex items-center gap-2"><span className="text-green-600">✓</span><span className="text-sm text-green-700 font-mono">{capturedBarcode}</span><button onClick={() => setCapturedBarcode("")} className="ml-auto text-green-600 hover:text-green-800 text-xs">Clear</button></div>)}
          </div>
          {scanError && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{scanError}</div>}
          <button onClick={handleScan} disabled={!selectedFile} className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed text-base py-3">{capturedBarcode ? t("consumer.scanLabelBarcode", { code: capturedBarcode }) : t("consumer.scanLabelBtn")}</button>
        </>
      )}
      {screen === "barcode" && <BarcodeScanner onDetected={(code) => { setCapturedBarcode(code); setScreen("upload"); }} onCancel={() => setScreen("upload")} onError={(msg) => { setScanError(msg); setScreen("upload"); }} />}
      {screen === "processing" && <ProcessingScreen />}
      {screen === "results" && <ResultsScreen report={lastResult} onScanAgain={() => { setLastResult(null); setScreen("upload"); }} />}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">{t("consumer.myScans")}</h2>
        {historyLoading ? <p className="text-gray-500">{t("common.loading")}</p> : scans.length === 0 ? <p className="text-gray-500">{t("consumer.noScans")}</p> : (
          <div className="space-y-3">
            {scans.map((scan) => (
              <div key={scan.id} onClick={() => setSelectedScan(selectedScan?.id === scan.id ? null : scan)} className={"p-4 rounded-lg cursor-pointer transition-colors border " + (selectedScan?.id === scan.id ? "bg-primary-50 border-primary-200" : "bg-gray-50 border-transparent hover:bg-gray-100")}>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0"><p className="text-sm font-medium text-gray-900 truncate">{scan.extracted_text?.substring(0, 80) || "No text"}</p><p className="text-xs text-gray-500 mt-0.5">{new Date(scan.created_at).toLocaleString()}</p></div>
                  <span className={"px-2.5 py-1 rounded-full text-xs font-semibold ml-3 " + (scan.compliance_score >= 80 ? "bg-green-100 text-green-800" : scan.compliance_score >= 50 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800")}>{scan.compliance_score}%</span>
                </div>
                {selectedScan?.id === scan.id && (<div className="mt-3 pt-3 border-t border-gray-200">
                  {scan.extracted_text && <p className="text-xs text-gray-600 bg-white rounded p-2 border border-gray-100 whitespace-pre-wrap max-h-24 overflow-y-auto font-mono">{scan.extracted_text}</p>}
                  {(() => { const m = parseMissingFields(scan.missing_fields); if (m.length === 0) return <p className="text-xs text-green-600 font-medium">All fields present</p>; return <div><p className="text-xs font-medium text-red-600 mb-1">Missing: </p><div className="flex flex-wrap gap-1">{m.map((f, i) => <span key={i} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">{f}</span>)}</div></div>; })()}
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    {reportSuccess === scan.id ? (
                      <div className="flex items-center gap-2 text-sm text-green-700">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        {t("consumer.reportSubmitted")}
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder={t("consumer.reportReason")}
                            value={reportReason}
                            onChange={(e) => setReportReason(e.target.value)}
                            className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                          />
                          <button
                            onClick={(e) => { e.stopPropagation(); handleReport(scan.id); }}
                            disabled={reportingId === scan.id}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors disabled:opacity-50"
                          >
                            {reportingId === scan.id ? t("consumer.reporting") : t("consumer.reportProduct")}
                          </button>
                        </div>
                        {reportError && <p className="text-xs text-red-600">{reportError}</p>}
                      </div>
                    )}
                  </div>
                </div>)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
