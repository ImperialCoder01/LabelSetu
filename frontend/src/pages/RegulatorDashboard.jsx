import { useState, useEffect, useMemo, useCallback } from "react";
import { supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

const REPORT_TYPES = [
  { value: "VIOLATION", label: "Mandatory Declaration Violation (Rule 6)" },
  { value: "SUSPECTED_COUNTERFEIT", label: "Suspected Counterfeit / Clone" },
  { value: "INFO_DISCREPANCY", label: "Product Specification Discrepancy" },
  { value: "PACKAGING_DISCREPANCY", label: "Packaging Artwork Tampering" },
  { value: "MISSING_DECLARATION", label: "Missing Statutory Declaration" },
  { value: "MANUFACTURER_ISSUE", label: "Manufacturer Address Untraceable" },
  { value: "CONSUMER_COMPLAINT", label: "Consumer Grievance Investigation" },
];

const RECOMMENDED_ACTIONS = [
  { value: "WARNING_NOTICE", label: "Issue Statutory Warning Notice" },
  { value: "SUSPEND_PRODUCT", label: "Recommend Product Suspension" },
  { value: "PRODUCT_RECALL", label: "Recommend Batch Recall" },
  { value: "SEIZE_BATCH", label: "Recommend Market Seizure" },
  { value: "REQUEST_INFO", label: "Request Clarification from Manufacturer" },
  { value: "FURTHER_INVESTIGATION", label: "Schedule On-Site Inspection" },
  { value: "NO_ACTION", label: "No Action / False Positive" },
];

export default function RegulatorDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("cases"); // 'cases' | 'new_case' | 'scans' | 'grievances'
  const [cases, setCases] = useState([]);
  const [scans, setScans] = useState([]);
  const [flaggedReports, setFlaggedReports] = useState([]);
  const [loading, setLoading] = useState(true);

  // New Case Form State
  const [submittingCase, setSubmittingCase] = useState(false);
  const [caseSuccess, setCaseSuccess] = useState(false);
  const [caseError, setCaseError] = useState(null);
  const [caseForm, setCaseForm] = useState({
    barcode: "",
    product_id: "",
    report_type: "VIOLATION",
    severity: "HIGH",
    description: "",
    detected_issue: "",
    applicable_rule: "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)",
    executive_observations: "",
    recommended_action: "WARNING_NOTICE",
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      // 1. Fetch Executive Cases
      const casesRes = await fetch(`${API_BASE}/api/executive-reports`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (casesRes.ok) {
        const cData = await casesRes.json();
        setCases(cData || []);
      }

      // 2. Fetch Scans (Backend API with Supabase fallback)
      try {
        const sRes = await fetch(`${API_BASE}/api/scans/?all=true&limit=100`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          if (Array.isArray(sData)) setScans(sData);
        } else {
          const scansRes = await supabase
            .from("scans")
            .select("*, users_profile!scans_user_id_fkey(full_name, role)")
            .order("created_at", { ascending: false })
            .limit(100);
          if (!scansRes.error) setScans(scansRes.data || []);
        }
      } catch (scansErr) {
        const scansRes = await supabase
          .from("scans")
          .select("*, users_profile!scans_user_id_fkey(full_name, role)")
          .order("created_at", { ascending: false })
          .limit(100);
        if (!scansRes.error) setScans(scansRes.data || []);
      }

      // 3. Fetch Forwarded Reports
      const repsRes = await supabase
        .from("product_reports")
        .select("*, scans(extracted_text, compliance_score)")
        .eq("status", "forwarded")
        .order("created_at", { ascending: false });
      if (!repsRes.error) setFlaggedReports(repsRes.data || []);
    } catch (err) {
      console.error("Failed to load regulator data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCaseSubmit = async (e) => {
    e.preventDefault();
    setSubmittingCase(true);
    setCaseError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Authentication required");

      const res = await fetch(`${API_BASE}/api/executive-reports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(caseForm),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to submit executive report");
      }

      setCaseSuccess(true);
      fetchData();
      setTimeout(() => {
        setCaseSuccess(false);
        setActiveTab("cases");
        setCaseForm({
          barcode: "",
          product_id: "",
          report_type: "VIOLATION",
          severity: "HIGH",
          description: "",
          detected_issue: "",
          applicable_rule: "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)",
          executive_observations: "",
          recommended_action: "WARNING_NOTICE",
        });
      }, 2000);
    } catch (err) {
      setCaseError(err.message);
    } finally {
      setSubmittingCase(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Executive Officer Enforcement Workspace</h1>
          <p className="text-xs text-slate-500 mt-1">Investigate non-compliance, build evidence cases & recommend regulatory actions</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab("cases")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "cases" ? "bg-slate-900 text-white shadow" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            📋 Investigation Cases ({cases.length})
          </button>
          <button
            onClick={() => setActiveTab("new_case")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "new_case" ? "bg-indigo-600 text-white shadow" : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            }`}
          >
            ➕ Open New Case
          </button>
          <button
            onClick={() => setActiveTab("scans")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "scans" ? "bg-emerald-600 text-white shadow" : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
            }`}
          >
            📊 Market Scans Telemetry
          </button>
          <button
            onClick={() => setActiveTab("grievances")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "grievances" ? "bg-rose-600 text-white shadow" : "bg-rose-50 text-rose-700 hover:bg-rose-100"
            }`}
          >
            🚨 Consumer Grievance Queue ({flaggedReports.length})
          </button>
        </div>
      </div>

      {/* TAB 1: CASES LIST */}
      {activeTab === "cases" && (
        <div className="space-y-4">
          {loading ? (
            <div className="card-slate p-8 text-center text-slate-400 font-bold">Loading investigation cases...</div>
          ) : cases.length === 0 ? (
            <div className="card-slate p-12 text-center space-y-3">
              <div className="text-4xl">⚖️</div>
              <h3 className="text-base font-extrabold text-slate-800">No Enforcement Cases Filed Yet</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Open investigation cases on products with severe Legal Metrology violations, suspected counterfeits, or price overcharging to recommend administrative action.
              </p>
              <button
                onClick={() => setActiveTab("new_case")}
                className="btn-accent px-6 py-2.5 text-xs inline-block mt-2"
              >
                Open First Investigation Case
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cases.map((c) => (
                <div key={c.id} className="card-slate p-5 space-y-3 border hover:border-slate-400 transition-all">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-mono text-[11px] font-black text-indigo-700">{c.case_number}</span>
                      <h3 className="text-sm font-black text-slate-900 mt-0.5">{c.description}</h3>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                      c.severity === "CRITICAL" ? "bg-rose-100 text-rose-800" : c.severity === "HIGH" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
                    }`}>
                      {c.severity}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl space-y-1 text-xs font-mono text-slate-600">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Barcode / SKU:</span>
                      <span className="font-bold text-slate-900">{c.barcode || "N/A"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Recommendation:</span>
                      <span className="font-bold text-indigo-800">{c.recommended_action}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Admin Status:</span>
                      <span className={`font-bold ${
                        c.status === "APPROVED" ? "text-emerald-700" : c.status === "REJECTED" ? "text-rose-700" : "text-amber-700"
                      }`}>{c.status}</span>
                    </div>
                  </div>

                  {c.admin_comments && (
                    <div className="p-2.5 bg-slate-100 rounded-lg text-xs text-slate-700">
                      <strong className="block text-[10px] uppercase text-slate-500 font-bold">Admin Decision Comments:</strong>
                      {c.admin_comments}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: OPEN NEW CASE */}
      {activeTab === "new_case" && (
        <div className="card-slate p-6 sm:p-8 max-w-3xl mx-auto space-y-6">
          <div>
            <h2 className="text-lg font-black text-slate-900">Initiate Enforcement Investigation Case</h2>
            <p className="text-xs text-slate-500">Document evidence and submit enforcement recommendation to Administrative Authority</p>
          </div>

          {caseSuccess && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold">
              ✓ Investigation case submitted successfully to Admin Approval Queue!
            </div>
          )}

          {caseError && (
            <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-bold">
              ⚠️ {caseError}
            </div>
          )}

          <form onSubmit={handleCaseSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Target Barcode / GTIN *</label>
                <input
                  type="text"
                  required
                  value={caseForm.barcode}
                  onChange={(e) => setCaseForm((prev) => ({ ...prev, barcode: e.target.value }))}
                  placeholder="e.g. 8901262010053"
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-mono outline-none"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">Investigation Severity *</label>
                <select
                  value={caseForm.severity}
                  onChange={(e) => setCaseForm((prev) => ({ ...prev, severity: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 outline-none font-bold"
                >
                  <option value="LOW">🟡 Low (Minor Formatting Issue)</option>
                  <option value="MEDIUM">🟠 Medium (Missing Optional Declaration)</option>
                  <option value="HIGH">🔴 High (Missing Critical Declaration / Price Inflated)</option>
                  <option value="CRITICAL">🚨 Critical (Counterfeit / Serious Tampering)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Violation Category *</label>
              <select
                value={caseForm.report_type}
                onChange={(e) => setCaseForm((prev) => ({ ...prev, report_type: e.target.value }))}
                className="w-full p-2.5 rounded-lg border border-slate-300 outline-none"
              >
                {REPORT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Case Description & Findings *</label>
              <textarea
                rows={3}
                required
                value={caseForm.description}
                onChange={(e) => setCaseForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Describe the detected non-compliance or physical packaging defect observed..."
                className="w-full p-2.5 rounded-lg border border-slate-300 outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Applicable Statutory Rule</label>
                <input
                  type="text"
                  value={caseForm.applicable_rule}
                  onChange={(e) => setCaseForm((prev) => ({ ...prev, applicable_rule: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 outline-none"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">Executive Recommended Action *</label>
                <select
                  value={caseForm.recommended_action}
                  onChange={(e) => setCaseForm((prev) => ({ ...prev, recommended_action: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 outline-none font-bold text-indigo-900"
                >
                  {RECOMMENDED_ACTIONS.map((a) => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <button
                type="button"
                onClick={() => setActiveTab("cases")}
                className="btn-secondary px-5 py-2 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingCase || !caseForm.barcode || !caseForm.description}
                className="btn-accent px-7 py-2 text-xs bg-indigo-600 hover:bg-indigo-700"
              >
                {submittingCase ? "Submitting..." : "Submit to Admin Review Queue →"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 3: SCANS TELEMETRY (PRESERVED) */}
      {activeTab === "scans" && (
        <div className="space-y-4">
          <div className="card-slate p-6">
            <h3 className="text-sm font-black text-slate-900 mb-3">Ecosystem-Wide Market Packaging Scans</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="p-3">User</th>
                    <th className="p-3">Compliance Score</th>
                    <th className="p-3">Extracted Snippet</th>
                    <th className="p-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scans.slice(0, 20).map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="p-3 font-bold text-slate-900">{s.users_profile?.full_name || "Consumer"}</td>
                      <td className="p-3">
                        <span className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                          s.compliance_score >= 80 ? "bg-emerald-100 text-emerald-800" : s.compliance_score >= 50 ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-800"
                        }`}>
                          {s.compliance_score !== null ? `${s.compliance_score}/100` : "N/A"}
                        </span>
                      </td>
                      <td className="p-3 text-slate-600 truncate max-w-xs">{s.extracted_text || "Image scan"}</td>
                      <td className="p-3 text-slate-400 font-mono">{new Date(s.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GRIEVANCES */}
      {activeTab === "grievances" && (
        <div className="space-y-4">
          <div className="card-slate p-6">
            <h3 className="text-sm font-black text-slate-900 mb-3">Consumer Grievances Forwarded for Investigation</h3>
            {flaggedReports.length === 0 ? (
              <p className="text-xs text-slate-400">No forwarded consumer grievances pending investigation.</p>
            ) : (
              <div className="space-y-3">
                {flaggedReports.map((r) => (
                  <div key={r.id} className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                    <div className="flex justify-between font-bold">
                      <span className="text-rose-700 font-black">Complaint ID: {r.id.substring(0, 8)}</span>
                      <span className="text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-slate-800 font-medium">{r.reason}</p>
                    <button
                      onClick={() => {
                        setCaseForm((prev) => ({
                          ...prev,
                          description: `Consumer grievance investigation: ${r.reason}`,
                          detected_issue: r.reason,
                        }));
                        setActiveTab("new_case");
                      }}
                      className="btn-accent text-[11px] px-3 py-1 mt-2 inline-block"
                    >
                      Convert to Enforcement Case →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
