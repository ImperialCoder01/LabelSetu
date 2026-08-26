import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../lib/supabase";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function BulkUpload({ onUploadComplete }) {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  const addFiles = useCallback((newFiles) => {
    const images = Array.from(newFiles).filter(f => f.type.startsWith("image/"));
    setFiles(prev => [...prev, ...images]);
  }, []);

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); };
  const removeFile = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx));

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setProgress({ done: 0, total: files.length });
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Not authenticated");
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("file", files[i]);
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
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Bulk Upload</h2>
      <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} className={"border-2 border-dashed rounded-xl p-8 text-center transition-colors " + (dragOver ? "border-primary-500 bg-primary-50" : "border-gray-300 hover:border-gray-400")}>
        <svg className="w-10 h-10 text-gray-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
        <p className="text-gray-600 font-medium text-sm">Drag & drop multiple label images</p>
        <p className="text-xs text-gray-400 mt-1">or</p>
        <label htmlFor="bulk-file-input" className="inline-block mt-2 px-4 py-2 rounded-lg bg-primary-50 text-primary-700 text-sm font-medium cursor-pointer hover:bg-primary-100 transition-colors">Browse Files</label>
        <input ref={fileRef} id="bulk-file-input" type="file" accept="image/*" multiple onChange={(e) => addFiles(e.target.files)} className="hidden" />
      </div>
      {files.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">{files.length} file(s) selected</p>
            <button onClick={() => setFiles([])} className="text-xs text-red-500 hover:text-red-700">Clear all</button>
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {files.map((file, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-gray-50 rounded px-3 py-1.5">
                <span className="text-gray-700 truncate mr-2">{file.name}</span>
                <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500 flex-shrink-0">&times;</button>
              </div>
            ))}
          </div>
          {uploading ? (
            <div className="mt-3">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-primary-500 h-2 rounded-full transition-all duration-300" style={{ width: (progress.done / progress.total * 100) + "%" }} />
              </div>
              <p className="text-xs text-gray-500 mt-1 text-center">Processing {progress.done} of {progress.total}...</p>
            </div>
          ) : (
            <button onClick={handleUpload} className="btn-primary w-full mt-3">Upload &amp; Scan {files.length} Label(s)</button>
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

  useEffect(() => { fetchScans(); }, []);

  async function fetchScans() {
    setLoading(true);
    const { data, error } = await supabase.from("scans").select("*").eq("user_id", user.id).order("created_at", { ascending: false });
    if (!error) setScans(data);
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
      if (!res.ok) throw new Error("Failed to generate certificate");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "certificate-" + scanId.substring(0, 8) + ".pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      setDownloading(null);
    }
  }

  const avgScore = scans.length > 0 ? Math.round(scans.reduce((acc, s) => acc + (s.compliance_score || 0), 0) / scans.length) : 0;
  const compliant = scans.filter(s => s.compliance_score >= 80).length;
  const issues = scans.filter(s => s.compliance_score < 80).length;

  return (
    <div className="space-y-8">
      <div><h1 className="text-2xl font-bold text-gray-900">Brand Dashboard</h1><p className="text-gray-500 mt-1">Manage your product label compliance</p></div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card"><p className="text-sm text-gray-500">Total SKUs</p><p className="text-3xl font-bold text-gray-900">{scans.length}</p></div>
        <div className="card"><p className="text-sm text-gray-500">Avg Score</p><p className={"text-3xl font-bold " + (avgScore >= 80 ? "text-green-600" : avgScore >= 50 ? "text-yellow-600" : "text-red-600")}>{avgScore}%</p></div>
        <div className="card"><p className="text-sm text-gray-500">Compliant</p><p className="text-3xl font-bold text-green-600">{compliant}</p></div>
        <div className="card"><p className="text-sm text-gray-500">Issues</p><p className="text-3xl font-bold text-red-600">{issues}</p></div>
      </div>

      {/* Bulk Upload */}
      <BulkUpload onUploadComplete={fetchScans} />

      {/* SKU Table */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Uploaded SKUs</h2>
        {loading ? <p className="text-gray-500">Loading...</p> : scans.length === 0 ? <p className="text-gray-500">No scans yet. Upload product labels to get started.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-3 px-3 font-medium text-gray-500">Date</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Product / SKU</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Score</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Status</th>
                  <th className="py-3 px-3 font-medium text-gray-500 text-right">Certificate</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => {
                  const score = scan.compliance_score || 0;
                  const status = score >= 80 ? "Compliant" : score >= 50 ? "Partial" : "Non-Compliant";
                  const statusClass = score >= 80 ? "bg-green-100 text-green-800" : score >= 50 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
                  const productName = (scan.extracted_text || "").split(String.fromCharCode(10))[0].substring(0, 50) || "—";
                  return (
                    <tr key={scan.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-3 text-gray-500 text-xs">{new Date(scan.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-3"><p className="font-medium text-gray-900 truncate max-w-xs">{productName}</p><p className="text-xs text-gray-400 font-mono">{scan.id.substring(0, 8)}</p></td>
                      <td className="py-3 px-3"><span className={"font-bold " + (score >= 80 ? "text-green-600" : score >= 50 ? "text-yellow-600" : "text-red-600")}>{score}%</span></td>
                      <td className="py-3 px-3"><span className={"px-2 py-1 rounded-full text-xs font-medium " + statusClass}>{status}</span></td>
                      <td className="py-3 px-3 text-right">
                        <button onClick={() => downloadCertificate(scan.id)} disabled={downloading === scan.id} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-50 text-primary-700 hover:bg-primary-100 disabled:opacity-50 transition-colors">
                          {downloading === scan.id ? <span className="w-3 h-3 border-2 border-primary-300 border-t-primary-600 rounded-full animate-spin" /> : <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12l-3-3m0 0l-3 3m3-3v11.25" /></svg>}
                          Download PDF
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
