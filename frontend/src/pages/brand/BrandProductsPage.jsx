import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";
import AppDrawer from "../../components/AppDrawer";

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

function BulkUpload({ onUploadComplete }) {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  const addFiles = useCallback((newFiles) => {
    const images = Array.from(newFiles).filter((f) => f.type.startsWith("image/"));
    setFiles((prev) => [...prev, ...images]);
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const removeFile = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setProgress({ done: 0, total: files.length });
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Authentication required");

      for (let i = 0; i < files.length; i++) {
        const optimized = await optimizeImageForUpload(files[i]);
        const formData = new FormData();
        formData.append("files", optimized);
        await fetch(API_BASE + "/api/scans/scan", {
          method: "POST",
          headers: { Authorization: "Bearer " + session.access_token },
          body: formData,
        });
        setProgress({ done: i + 1, total: files.length });
      }
      setFiles([]);
      onUploadComplete();
    } catch (err) {
      alert("Bulk upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card-slate p-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Bulk Packaging Verification</h3>
          <p className="text-xs text-slate-500">Audit multiple SKU label proofs simultaneously</p>
        </div>
        {files.length > 0 && (
          <span className="text-xs font-bold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
            {files.length} files staged
          </span>
        )}
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-6 sm:p-8 text-center transition-all ${
          dragOver ? "border-emerald-500 bg-emerald-50/50" : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
        }`}
      >
        <span className="text-2xl mb-1 inline-block">📦</span>
        <p className="text-xs font-bold text-slate-800">Drag & drop SKU label images</p>
        <p className="text-[11px] text-slate-400 mt-0.5">PNG, JPEG, WebP</p>
        <label
          htmlFor="bulk-file-input"
          className="inline-block mt-3 px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-bold cursor-pointer hover:bg-slate-800 transition-colors"
        >
          Browse Files
        </label>
        <input
          ref={fileRef}
          id="bulk-file-input"
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => addFiles(e.target.files)}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold">
            <span className="text-slate-600">{files.length} SKU label(s) staged</span>
            <button onClick={() => setFiles([])} className="text-red-600 hover:underline">Clear all</button>
          </div>

          <div className="max-h-36 overflow-y-auto space-y-1.5 custom-scrollbar">
            {files.map((file, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-slate-50 p-2 rounded-lg border border-slate-200">
                <span className="text-slate-700 font-mono truncate mr-2">{file.name}</span>
                <button onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-600 font-bold">&times;</button>
              </div>
            ))}
          </div>

          {uploading ? (
            <div className="space-y-1.5 pt-2">
              <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.done / progress.total) * 100}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 text-center font-bold">
                Auditing {progress.done} of {progress.total} SKUs...
              </p>
            </div>
          ) : (
            <button onClick={handleUpload} className="btn-accent w-full py-2.5 text-xs">
              Audit & Verify {files.length} SKU Labels
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function BrandDashboard() {
  const { user } = useAuth();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);
  const [selectedScan, setSelectedScan] = useState(null);

  useEffect(() => {
    fetchScans();
  }, [user]);

  async function fetchScans() {
    if (!user) return;
    setLoading(true);
    const { data, error } = await supabase
      .from("scans")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });
    if (!error && data) setScans(data);
    setLoading(false);
  }

  async function downloadCertificate(scanId) {
    setDownloading(scanId);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Not authenticated");
      const res = await fetch(API_BASE + "/api/scans/" + scanId + "/certificate", {
        headers: { Authorization: "Bearer " + session.access_token },
      });
      if (!res.ok) throw new Error("Failed to generate compliance certificate");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "compliance-certificate-" + scanId.substring(0, 8) + ".pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      setDownloading(null);
    }
  }

  const avgScore = scans.length > 0
    ? Math.round(scans.reduce((acc, s) => acc + (s.compliance_score || 0), 0) / scans.length)
    : 0;
  const compliant = scans.filter((s) => (s.compliance_score || 0) >= 80).length;
  const issues = scans.filter((s) => (s.compliance_score || 0) < 80).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-900 tracking-tight">Brand Compliance SaaS</h2>
          <p className="text-xs text-slate-500 mt-0.5">Manage SKU packaging compliance & generate Legal Metrology certificates</p>
        </div>
        <Link to="/brand/verify" className="btn-accent flex-shrink-0">
          <span>✨</span> Verify New SKU
        </Link>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="card-slate p-4 sm:p-5">
          <span className="text-xs font-bold text-slate-500 uppercase">Total Verified SKUs</span>
          <p className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">{scans.length}</p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <span className="text-xs font-bold text-slate-500 uppercase">Catalog Compliance Index</span>
          <p className={`text-2xl sm:text-3xl font-black mt-1 ${avgScore >= 80 ? "text-emerald-600" : "text-amber-600"}`}>
            {avgScore}%
          </p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <span className="text-xs font-bold text-slate-500 uppercase">Compliant SKUs</span>
          <p className="text-2xl sm:text-3xl font-black text-emerald-600 mt-1">{compliant}</p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <span className="text-xs font-bold text-slate-500 uppercase">Action Required</span>
          <p className="text-2xl sm:text-3xl font-black text-red-600 mt-1">{issues}</p>
        </div>
      </div>

      {/* Bulk Upload Component */}
      <BulkUpload onUploadComplete={fetchScans} />

      {/* SKU Table & History */}
      <div className="card-slate p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">SKU Compliance Catalog</h3>
            <p className="text-xs text-slate-500">Legal Metrology audit certificates for packaging proofs</p>
          </div>
        </div>

        {loading ? (
          <p className="text-xs text-slate-400 py-8 text-center">Loading SKU catalog...</p>
        ) : scans.length === 0 ? (
          <div className="py-12 text-center border border-dashed border-slate-200 rounded-xl">
            <p className="text-xs font-bold text-slate-600">No SKU audits recorded</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Upload packaging proofs to verify mandatory declarations.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider font-extrabold text-[10px]">
                  <th className="py-3 px-3">Date</th>
                  <th className="py-3 px-3">Product / SKU</th>
                  <th className="py-3 px-3">Score</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Certificate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {scans.map((scan) => {
                  const score = scan.compliance_score || 0;
                  const isPass = score >= 80;
                  const isPartial = score >= 50 && score < 80;
                  const dateStr = scan.created_at ? new Date(scan.created_at).toLocaleDateString("en-IN") : "Recent";
                  const productName = scan.product_name || (scan.extracted_text || "").split("\n")[0].substring(0, 40) || "SKU Label Proof";

                  return (
                    <tr key={scan.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-3 text-slate-400 font-mono">{dateStr}</td>
                      <td className="py-3 px-3">
                        <p className="font-bold text-slate-900 truncate max-w-xs">{productName}</p>
                        <span className="text-[10px] text-slate-400 font-mono">ID: {scan.id.substring(0, 8)}</span>
                      </td>
                      <td className="py-3 px-3 font-black">
                        <span className={isPass ? "text-emerald-600" : isPartial ? "text-amber-600" : "text-red-600"}>
                          {score}%
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          isPass ? "bg-emerald-50 text-emerald-700" : isPartial ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"
                        }`}>
                          {isPass ? "Compliant" : isPartial ? "Attention" : "Violation"}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => downloadCertificate(scan.id)}
                          disabled={downloading === scan.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-slate-900 hover:bg-slate-800 text-white disabled:opacity-50 transition-colors shadow-2xs"
                        >
                          {downloading === scan.id ? "Generating..." : "Download PDF"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
