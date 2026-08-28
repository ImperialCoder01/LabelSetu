import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../lib/supabase";
import { useTranslation } from "react-i18next";
import BarcodeScanner from "../components/BarcodeScanner";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

function UnitPriceComparator() {
  const [p1, setP1] = useState({ price: "50", qty: "200", unit: "g" });
  const [p2, setP2] = useState({ price: "110", qty: "500", unit: "g" });

  const cost1 = (parseFloat(p1.price) / parseFloat(p1.qty)) || 0;
  const cost2 = (parseFloat(p2.price) / parseFloat(p2.qty)) || 0;

  const diff = cost1 && cost2 ? Math.abs(((cost1 - cost2) / Math.max(cost1, cost2)) * 100).toFixed(1) : 0;
  const winner = cost1 < cost2 ? "Option 1" : cost1 > cost2 ? "Option 2" : "Equal";

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            Unit Sale Price Comparator (Rule 6)
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Compare cost per gram/ml across pack sizes to spot misleading prices
          </p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-green-100 text-green-800">
          Consumer Saver
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className={`p-3 rounded-lg border ${winner === "Option 1" ? "border-green-500 bg-green-50/50" : "border-gray-200 bg-gray-50"}`}>
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold text-gray-700">Option A (Small Pack)</span>
            {winner === "Option 1" && <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">Cheaper Choice ✓</span>}
          </div>
          <div className="flex gap-2">
            <input type="number" placeholder="Price (₹)" value={p1.price} onChange={(e) => setP1({...p1, price: e.target.value})} className="input-field text-xs flex-1" />
            <input type="number" placeholder="Qty" value={p1.qty} onChange={(e) => setP1({...p1, qty: e.target.value})} className="input-field text-xs flex-1" />
            <span className="text-xs font-medium self-center text-gray-500">{p1.unit}</span>
          </div>
          <p className="text-xs font-mono font-bold text-gray-800 mt-2">
            Unit Price: ₹{(cost1 * 100).toFixed(2)} / 100{p1.unit}
          </p>
        </div>

        <div className={`p-3 rounded-lg border ${winner === "Option 2" ? "border-green-500 bg-green-50/50" : "border-gray-200 bg-gray-50"}`}>
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold text-gray-700">Option B (Large Pack)</span>
            {winner === "Option 2" && <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">Cheaper Choice ✓</span>}
          </div>
          <div className="flex gap-2">
            <input type="number" placeholder="Price (₹)" value={p2.price} onChange={(e) => setP2({...p2, price: e.target.value})} className="input-field text-xs flex-1" />
            <input type="number" placeholder="Qty" value={p2.qty} onChange={(e) => setP2({...p2, qty: e.target.value})} className="input-field text-xs flex-1" />
            <span className="text-xs font-medium self-center text-gray-500">{p2.unit}</span>
          </div>
          <p className="text-xs font-mono font-bold text-gray-800 mt-2">
            Unit Price: ₹{(cost2 * 100).toFixed(2)} / 100{p2.unit}
          </p>
        </div>
      </div>

      {cost1 > 0 && cost2 > 0 && (
        <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 flex justify-between items-center">
          <span>
            <b>{winner}</b> is <b>{diff}% cheaper</b> per unit.
          </span>
          <span className="font-mono font-bold text-blue-700">
            Rule 6 Metric Compliant
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

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Scan Product Label(s)</h2>
          <p className="text-xs text-gray-500 mt-0.5">Upload one or multiple photos (e.g. Front + Back packaging panels)</p>
        </div>
        {selectedFiles.length > 0 && (
          <span className="text-xs font-bold px-2.5 py-1 rounded bg-blue-100 text-blue-800">
            {selectedFiles.length} Photo{selectedFiles.length > 1 ? "s" : ""} Selected
          </span>
        )}
      </div>

      {selectedFiles.length > 0 ? (
        <div className="space-y-3 mb-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {selectedFiles.map((file, idx) => (
              <div key={idx} className="relative rounded-lg border border-gray-200 bg-white p-2 flex flex-col items-center">
                <img src={URL.createObjectURL(file)} alt={`Preview ${idx + 1}`} className="w-full h-28 object-contain rounded mb-1" />
                <span className="text-[10px] font-mono text-gray-600 truncate w-full text-center">{file.name}</span>
                <button
                  onClick={() => onRemoveFile(idx)}
                  className="absolute top-1 right-1 bg-red-500 hover:bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs shadow-sm transition-colors"
                  title="Remove photo"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => fileRef.current?.click()}
            className="w-full py-2 border border-dashed border-gray-300 hover:border-gray-400 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            + Add Another Packaging Photo (e.g. Side or Back Panel)
          </button>
        </div>
      ) : (
        <div onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} className={"border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors " + (dragOver ? "border-primary-500 bg-primary-50" : "border-gray-300 hover:border-gray-400")}>
          <div className="mx-auto mb-3 w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-7 h-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" /></svg>
          </div>
          <p className="text-gray-600 font-medium">Click or Drag & Drop Product Photo(s)</p>
          <p className="text-xs text-gray-400 mt-1">Select 1 or multiple photos (PNG, JPEG, WebP)</p>
        </div>
      )}

      <input ref={fileRef} type="file" accept="image/*" multiple onChange={handleInputChange} className="hidden" id="file-upload" />
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
    { label: "Uploading & Validating Image(s)...", icon: "⬇️" },
    { label: "Running Preprocessing & OCR...", icon: "🔍" },
    { label: "Classifying Package Panels...", icon: "📦" },
    { label: "Aggregating Multi-Image Evidence...", icon: "⚖️" },
    { label: "Computing Legal Metrology Score...", icon: "✨" },
  ];
  return (
    <div className="card flex flex-col items-center py-12">
      <div className="relative w-20 h-20 mb-6">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
        <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
      </div>
      <p className="text-lg font-semibold text-gray-900 mb-6">Analyzing Package Evidence...</p>
      <div className="space-y-3 w-full max-w-xs">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3 text-sm text-gray-500 animate-pulse" style={{ animationDelay: (i * 300) + "ms" }}>
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
  const { compliance, ocr, barcode_lookup, manufacturer_mismatch, quality_info, classification, image_details } = report;
  const score = compliance.overall_score;
  const scoreColor = score >= 80 ? "text-green-600" : score >= 50 ? "text-yellow-500" : "text-red-600";
  const scoreBg = score >= 80 ? "bg-green-50" : score >= 50 ? "bg-yellow-50" : "bg-red-50";
  const scoreLabel = compliance.compliance_assessment || (score >= 80 ? "Compliant" : score >= 50 ? "Partial" : "Non-Compliant");
  const dashLen = 2 * Math.PI * 52;
  const dashOff = 2 * Math.PI * 52 * (1 - score / 100);

  return (
    <div className="space-y-6">
      {/* Evidence Coverage & Package Panels Header Card */}
      <div className="card bg-blue-50/50 border border-blue-200">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900">
            Evidence Coverage: {compliance.evidence_coverage || `${compliance.passed}/${compliance.total_fields} assessable`}
          </span>
          {compliance.captured_panels && (
            <div className="flex gap-1.5 flex-wrap">
              {compliance.captured_panels.map((p, idx) => (
                <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-200/70 text-blue-950">
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>

        {compliance.actions_required && compliance.actions_required.length > 0 && (
          <div className="mt-2 p-2.5 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-900">
            <span className="font-bold">Required Action:</span> {compliance.actions_required.join(" ")}
          </div>
        )}
      </div>

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
        <p className="text-xs text-gray-400 mt-2">Passed Declarations: {compliance.passed}/{compliance.total_fields}</p>
      </div>

      {/* Multi-Image Evidence Checklist */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Multi-Image Legal Metrology Evidence</h3>
        <div className="space-y-3">
          {compliance.fields.map((field) => {
            const evStatus = field.evidence_status || (field.status === "pass" ? "CONFIRMED_PRESENT" : "CONFIRMED_MISSING");
            let badgeBg = "bg-green-100 text-green-800";
            let icon = "✓";
            if (evStatus === "CONFIRMED_MISSING") { badgeBg = "bg-red-100 text-red-800"; icon = "✗"; }
            else if (evStatus === "NOT_VISIBLE") { badgeBg = "bg-blue-100 text-blue-800"; icon = "👁️"; }
            else if (evStatus === "UNREADABLE") { badgeBg = "bg-yellow-100 text-yellow-800"; icon = "⚠️"; }
            else if (evStatus === "NOT_DETECTED") { badgeBg = "bg-gray-100 text-gray-700"; icon = "🔍"; }
            else if (evStatus === "CONFLICTING_EVIDENCE") { badgeBg = "bg-purple-100 text-purple-800"; icon = "⚡"; }

            return (
              <div key={field.field_id} className={`p-3.5 rounded-lg border transition-colors ${evStatus === "CONFIRMED_PRESENT" ? "bg-green-50/50 border-green-200" : evStatus === "CONFIRMED_MISSING" ? "bg-red-50/50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{field.field_name}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${badgeBg}`}>
                        {icon} {evStatus}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{field.reason || field.description}</p>
                    {field.extracted_value && (
                      <p className="text-xs font-mono font-bold text-green-800 mt-1 bg-green-100/70 inline-block px-2 py-0.5 rounded">
                        Extracted Value: {field.extracted_value}
                      </p>
                    )}
                  </div>
                  {field.score_impact !== 0 && (
                    <span className="text-xs font-mono font-bold text-red-600 bg-red-100 px-2 py-0.5 rounded">
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
    const { data, error } = await supabase.from("scans").select("*").eq("user_id", user.id).order("created_at", { ascending: false });
    if (!error) setScans(data);
    setHistoryLoading(false);
  }

  function handleFilesSelected(newFiles) {
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  }

  function handleRemoveFile(idx) {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleScan() {
    if (selectedFiles.length === 0 && !capturedBarcode) return;
    setScreen("processing");
    setScanError(null);
    setLastResult(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.access_token) {
        throw new Error("Authentication session missing. Please sign in again.");
      }

      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append("files", file);
      });
      if (capturedBarcode) formData.append("barcode", capturedBarcode);

      let res;
      try {
        res = await fetch(`${API_BASE}/api/scans/scan`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
          body: formData,
        });
      } catch (netErr) {
        console.error("Browser fetch network/CORS error:", netErr);
        throw new Error("Browser could not connect to scanning server");
      }

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const detailMsg = errBody.detail || errBody.message;
        if (res.status === 401) throw new Error("Authentication failed");
        if (res.status === 403) throw new Error("You do not have permission to scan");
        if (res.status === 404) throw new Error("Scan API endpoint not found");
        if (res.status === 500) throw new Error("Server error while processing the image");
        if (res.status === 502 || res.status === 503 || res.status === 504) {
          throw new Error("Scanning server temporarily unavailable");
        }
        throw new Error(`Scan failed (${res.status}): ${detailMsg || res.statusText}`);
      }

      const result = await res.json();
      setLastResult(result);
      setSelectedFiles([]);
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
          <UploadScreen onFilesSelected={handleFilesSelected} selectedFiles={selectedFiles} onRemoveFile={handleRemoveFile} />
          <div className="card">
            <div className="flex items-center justify-between">
              <div><h3 className="text-sm font-semibold text-gray-900">Barcode Lookup</h3><p className="text-xs text-gray-500 mt-0.5">Scan barcode to cross-reference with Open Food Facts</p></div>
              <button onClick={() => setScreen("barcode")} className="px-4 py-2 rounded-lg bg-primary-50 text-primary-700 text-sm font-medium hover:bg-primary-100 transition-colors">{t("consumer.scanBarcode")}</button>
            </div>
            {capturedBarcode && (<div className="mt-3 p-2 bg-green-50 rounded-lg flex items-center gap-2"><span className="text-green-600">✓</span><span className="text-sm text-green-700 font-mono">{capturedBarcode}</span><button onClick={() => setCapturedBarcode("")} className="ml-auto text-green-600 hover:text-green-800 text-xs">Clear</button></div>)}
          </div>
          {scanError && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{scanError}</div>}
          <button onClick={handleScan} disabled={selectedFiles.length === 0 && !capturedBarcode} className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed text-base py-3">
            {capturedBarcode ? (selectedFiles.length > 0 ? `Scan ${selectedFiles.length} Packaging Photo(s) & Cross-Check Barcode` : "Lookup Barcode " + capturedBarcode) : (selectedFiles.length > 1 ? `Scan ${selectedFiles.length} Packaging Photos` : t("consumer.scanLabelBtn"))}
          </button>
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
      <UnitPriceComparator />
    </div>
  );
}
