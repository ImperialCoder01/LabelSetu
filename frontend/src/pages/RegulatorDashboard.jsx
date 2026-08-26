import { useState, useEffect, useMemo } from "react";
import { supabase } from "../lib/supabase";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from "recharts";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

// Field ID to human-readable name mapping
const FIELD_NAMES = {
  manufacturer_name_address: "Manufacturer Name & Address",
  product_name: "Product Name",
  net_quantity: "Net Quantity",
  manufacturing_date: "Manufacturing Date",
  mrp: "Maximum Retail Price (MRP)",
  consumer_care_contact: "Consumer Care Contact",
  unit_sale_price: "Unit Sale Price",
  country_of_origin: "Country of Origin",
  barcode_brand_match: "Barcode-Brand Match",
};

function parseMissingFields(mf) {
  if (!mf) return [];
  const raw = typeof mf === "string" ? JSON.parse(mf) : mf;
  return Array.isArray(raw) ? raw : [];
}

function TopFailedFieldsChart({ scans }) {
  const data = useMemo(() => {
    const counts = {};
    scans.forEach(scan => {
      parseMissingFields(scan.missing_fields).forEach(f => {
        counts[f] = (counts[f] || 0) + 1;
      });
    });
    return Object.entries(counts)
      .map(([id, count]) => ({ field: FIELD_NAMES[id] || id, count, id }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [scans]);

  if (data.length === 0) return <p className="text-gray-500 text-sm">No violation data available.</p>;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Most Failed Fields</h3>
      <div style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="field" width={180} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(val) => [val + " scans", "Failures"]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
            <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
function ScoreTrendChart({ scans }) {
  const data = useMemo(() => {
    const byDate = {};
    scans.forEach(scan => {
      const date = scan.created_at ? scan.created_at.substring(0, 10) : null;
      if (!date) return;
      if (!byDate[date]) byDate[date] = { scores: [], count: 0 };
      byDate[date].scores.push(scan.compliance_score || 0);
      byDate[date].count++;
    });
    return Object.entries(byDate)
      .map(([date, d]) => ({ date, avg: Math.round(d.scores.reduce((a, b) => a + b, 0) / d.count), count: d.count }))
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-30);
  }, [scans]);

  if (data.length === 0) return <p className="text-gray-500 text-sm">No trend data available.</p>;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Compliance Score Trend</h3>
      <div style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.substring(5)} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(val) => [val + "%", "Avg Score"]} labelFormatter={(l) => "Date: " + l} />
            <Line type="monotone" dataKey="avg" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
export default function RegulatorDashboard() {
  const [scans, setScans] = useState([]);
  const [flaggedReports, setFlaggedReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scoreFilter, setScoreFilter] = useState("all");
  const [violationFilter, setViolationFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [reviewLoading, setReviewLoading] = useState(null);

  useEffect(() => { fetchAllScans(); fetchFlaggedReports(); }, []);

  async function fetchAllScans() {
    const { data, error } = await supabase
      .from("scans")
      .select("*, users_profile!scans_user_id_fkey(full_name, role)")
      .order("created_at", { ascending: false });
    if (!error) setScans(data);
    setLoading(false);
  }

  async function fetchFlaggedReports() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      const res = await fetch(API_BASE + "/api/reports/flagged", {
        headers: { Authorization: "Bearer " + session.access_token },
      });
      if (res.ok) {
        const data = await res.json();
        setFlaggedReports(data);
      }
    } catch (err) {
      console.error("Failed to fetch flagged reports:", err);
    }
  }

  async function handleReview(reportId) {
    setReviewLoading(reportId);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(API_BASE + "/api/reports/" + reportId + "/review", {
        method: "PATCH",
        headers: { Authorization: "Bearer " + session.access_token },
      });
      if (res.ok) {
        setFlaggedReports(prev => prev.filter(r => r.id !== reportId));
      }
    } catch (err) {
      console.error("Review failed:", err);
    } finally {
      setReviewLoading(null);
    }
  }

  // Compute derived filter options
  const allViolationTypes = useMemo(() => {
    const types = new Set();
    scans.forEach(scan => {
      parseMissingFields(scan.missing_fields).forEach(f => types.add(f));
    });
    return Array.from(types).sort();
  }, [scans]);

  // Apply filters
  const filteredScans = useMemo(() => {
    return scans.filter(scan => {
      // Score filter
      if (scoreFilter === "high" && scan.compliance_score < 80) return false;
      if (scoreFilter === "medium" && (scan.compliance_score < 50 || scan.compliance_score >= 80)) return false;
      if (scoreFilter === "low" && scan.compliance_score >= 50) return false;
      // Violation type filter
      if (violationFilter !== "all") {
        const missing = parseMissingFields(scan.missing_fields);
        if (!missing.includes(violationFilter)) return false;
      }
      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const text = (scan.extracted_text || "").toLowerCase();
        const name = (scan.users_profile?.full_name || "").toLowerCase();
        if (!text.includes(q) && !name.includes(q)) return false;
      }
      return true;
    });
  }, [scans, scoreFilter, violationFilter, searchQuery]);

  // Stats
  const stats = useMemo(() => ({
    total: scans.length,
    high: scans.filter(s => s.compliance_score >= 80).length,
    medium: scans.filter(s => s.compliance_score >= 50 && s.compliance_score < 80).length,
    low: scans.filter(s => s.compliance_score < 50).length,
    avg: scans.length > 0 ? Math.round(scans.reduce((a, s) => a + (s.compliance_score || 0), 0) / scans.length) : 0,
  }), [scans]);

  return (
    <div className="space-y-8">
      <div><h1 className="text-2xl font-bold text-gray-900">Regulator Dashboard</h1><p className="text-gray-500 mt-1">Monitor all product label compliance across brands</p></div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="card"><p className="text-sm text-gray-500">Total Scans</p><p className="text-3xl font-bold text-gray-900">{stats.total}</p></div>
        <div className="card"><p className="text-sm text-gray-500">Avg Score</p><p className={"text-3xl font-bold " + (stats.avg >= 80 ? "text-green-600" : stats.avg >= 50 ? "text-yellow-600" : "text-red-600")}>{stats.avg}%</p></div>
        <div className="card"><p className="text-sm text-gray-500">Compliant</p><p className="text-3xl font-bold text-green-600">{stats.high}</p></div>
        <div className="card"><p className="text-sm text-gray-500">Partial</p><p className="text-3xl font-bold text-yellow-600">{stats.medium}</p></div>
        <div className="card"><p className="text-sm text-gray-500">Non-Compliant</p><p className="text-3xl font-bold text-red-600">{stats.low}</p></div>
      </div>

      {/* Flagged Reports */}
      {flaggedReports.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v1.5M3 21v-6m0 0l2.77-.693a9 9 0 016.208.682l.108.054a9 9 0 006.086.71l3.114-.732a48.524 48.524 0 01-.005-10.499l-3.11.732a9 9 0 01-6.085-.711l-.108-.054a9 9 0 00-6.208-.682L3 4.5M3 15V4.5" />
            </svg>
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Flagged Reports from Consumers</h3>
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">
              {flaggedReports.length}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 px-3 font-medium text-gray-500">Date</th>
                  <th className="py-2 px-3 font-medium text-gray-500">Reporter</th>
                  <th className="py-2 px-3 font-medium text-gray-500">Brand</th>
                  <th className="py-2 px-3 font-medium text-gray-500">Score</th>
                  <th className="py-2 px-3 font-medium text-gray-500">Reason</th>
                  <th className="py-2 px-3 font-medium text-gray-500 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {flaggedReports.map(report => (
                  <tr key={report.id} className="border-b border-gray-50 hover:bg-red-50 transition-colors">
                    <td className="py-3 px-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(report.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-3 text-gray-900">
                      {report.users_profile?.full_name || "Unknown"}
                    </td>
                    <td className="py-3 px-3">
                      <p className="text-gray-900 truncate max-w-[150px]">
                        {report.scans?.extracted_text?.substring(0, 40) || "—"}
                      </p>
                      <p className="text-xs text-gray-400">
                        {report.scans?.users_profile?.full_name || "—"}
                      </p>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`font-bold text-sm ${
                        report.scans?.compliance_score >= 80 ? "text-green-600" :
                        report.scans?.compliance_score >= 50 ? "text-yellow-600" : "text-red-600"
                      }`}>
                        {report.scans?.compliance_score ?? "—"}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-gray-600 text-xs max-w-[120px] truncate">
                      {report.reason || "—"}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleReview(report.id)}
                        disabled={reviewLoading === report.id}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors disabled:opacity-50"
                      >
                        {reviewLoading === report.id ? "Reviewing…" : "Mark Reviewed"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopFailedFieldsChart scans={scans} />
        <ScoreTrendChart scans={scans} />
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-gray-700">Filters:</span>
          <div className="flex gap-1.5">
            {["all", "high", "medium", "low"].map(f => (
              <button key={f} onClick={() => setScoreFilter(f)} className={"px-3 py-1.5 rounded-lg text-xs font-medium transition-colors " + (scoreFilter === f ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200")}>
                {f === "all" ? "All Scores" : f === "high" ? "Compliant (80+)" : f === "medium" ? "Partial (50-79)" : "Non-Compliant (<50)"}
              </button>
            ))}
          </div>
          {allViolationTypes.length > 0 && (
            <select value={violationFilter} onChange={(e) => setViolationFilter(e.target.value)} className="input-field text-xs py-1.5 w-auto">
              <option value="all">All Violation Types</option>
              {allViolationTypes.map(v => <option key={v} value={v}>{FIELD_NAMES[v] || v}</option>)}
            </select>
          )}
          <input type="text" placeholder="Search brand / text..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="input-field text-xs py-1.5 w-48" />
          <span className="text-xs text-gray-400 ml-auto">{filteredScans.length} of {scans.length} scans</span>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">All Scans</h3>
        {loading ? <p className="text-gray-500">Loading...</p> : filteredScans.length === 0 ? <p className="text-gray-500">No scans match the current filters.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200 text-left">
                <th className="py-3 px-3 font-medium text-gray-500">Date</th>
                <th className="py-3 px-3 font-medium text-gray-500">Brand / User</th>
                <th className="py-3 px-3 font-medium text-gray-500">Extracted Text</th>
                <th className="py-3 px-3 font-medium text-gray-500">Score</th>
                <th className="py-3 px-3 font-medium text-gray-500">Violations</th>
              </tr></thead>
              <tbody>
                {filteredScans.map((scan) => {
                  const missing = parseMissingFields(scan.missing_fields);
                  return (
                    <tr key={scan.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="py-3 px-3 text-gray-500 text-xs whitespace-nowrap">{new Date(scan.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-3"><p className="font-medium text-gray-900 text-sm">{scan.users_profile?.full_name || "Unknown"}</p><p className="text-xs text-gray-400 capitalize">{scan.users_profile?.role || ""}</p></td>
                      <td className="py-3 px-3 text-gray-700 max-w-xs truncate text-xs">{scan.extracted_text?.substring(0, 80) || "—"}</td>
                      <td className="py-3 px-3"><span className={"font-bold text-sm " + (scan.compliance_score >= 80 ? "text-green-600" : scan.compliance_score >= 50 ? "text-yellow-600" : "text-red-600")}>{scan.compliance_score}%</span></td>
                      <td className="py-3 px-3">
                        {missing.length === 0 ? <span className="text-xs text-green-600">None</span> : (
                          <div className="flex flex-wrap gap-1">{missing.map((f, i) => <span key={i} className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded" title={FIELD_NAMES[f] || f}>{(FIELD_NAMES[f] || f).substring(0, 20)}</span>)}</div>
                        )}
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
