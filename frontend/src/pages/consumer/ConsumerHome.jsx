import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";
import AppDrawer from "../../components/AppDrawer";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

function getScanTitle(scan) {
  if (scan.product_name && scan.product_name !== "Product Packaging") return scan.product_name;
  if (scan.brand) return `${scan.brand} Product`;
  if (scan.extracted_text) {
    const lines = scan.extracted_text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    if (lines.length > 0 && lines[0].length <= 50) return lines[0];
  }
  return "Packaging Scan";
}

export default function ConsumerHome() {
  const { profile, user } = useAuth();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedScan, setSelectedScan] = useState(null);

  const firstName = profile?.full_name
    ? profile.full_name.trim().split(" ")[0]
    : user?.email?.split("@")[0] || "Consumer";

  useEffect(() => {
    async function loadScans() {
      if (!user) return;
      try {
        setLoading(true);
        // Try backend API first with active token
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          try {
            const res = await fetch(`${API_BASE}/api/scans/?limit=10`, {
              headers: { Authorization: `Bearer ${session.access_token}` },
            });
            if (res.ok) {
              const data = await res.json();
              if (Array.isArray(data)) {
                setScans(data);
                setLoading(false);
                return;
              }
            }
          } catch (apiErr) {
            console.debug("Backend scans fetch fallback:", apiErr);
          }
        }

        // Direct supabase client fallback
        const { data, error } = await supabase
          .from("scans")
          .select("*")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false })
          .limit(10);
        if (!error && data) setScans(data);
      } catch (err) {
        console.error("Error loading consumer scans:", err);
      } finally {
        setLoading(false);
      }
    }
    loadScans();
  }, [user]);

  const totalScans = scans.length;
  const compliantScans = scans.filter((s) => (s.compliance_score || 0) >= 80).length;
  const flaggedScans = scans.filter((s) => (s.compliance_score || 0) < 80).length;
  const avgScore = totalScans > 0
    ? Math.round(scans.reduce((a, b) => a + (b.compliance_score || 0), 0) / totalScans)
    : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero Card */}
      <div className="card-slate bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 text-white p-6 sm:p-8 relative overflow-hidden shadow-lg border-slate-800">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800 text-[11px] font-bold mb-3">
            <span>🛡️</span> Legal Metrology AI Assistant
          </div>
          <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
            Hi, {firstName} 👋
          </h2>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed font-medium">
            Verify whether packaged commodities comply with the <strong className="text-emerald-400">Legal Metrology (Packaged Commodities) Rules, 2011</strong>. Catch hidden price inflation, missing manufacturer addresses, or invalid net weights before you purchase.
          </p>
          <div className="flex flex-wrap gap-3 mt-6">
            <Link
              to="/consumer/scan"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-slate-950 font-black text-xs uppercase tracking-wider shadow-md hover:shadow-lg transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
              </svg>
              <span>Scan Product Packaging</span>
            </Link>
            <Link
              to="/consumer/compare"
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-slate-800/90 hover:bg-slate-750 text-white font-bold text-xs border border-slate-700 transition-all"
            >
              <span>⚖️</span> Compare Unit Prices
            </Link>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="card-slate p-4 sm:p-5">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Scans Conducted</span>
            <span className="text-lg">🔍</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-slate-900">{totalScans}</p>
          <p className="text-[11px] text-slate-400 mt-1 font-medium">Packaging verifications</p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Compliant</span>
            <span className="text-lg">✅</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-emerald-600">{compliantScans}</p>
          <p className="text-[11px] text-slate-400 mt-1 font-medium">Passed all 8 rules</p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Issues Detected</span>
            <span className="text-lg">⚠️</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-amber-600">{flaggedScans}</p>
          <p className="text-[11px] text-slate-400 mt-1 font-medium">Missing declarations</p>
        </div>

        <div className="card-slate p-4 sm:p-5">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Avg Compliance</span>
            <span className="text-lg">📊</span>
          </div>
          <p className={`text-2xl sm:text-3xl font-black ${avgScore >= 80 ? "text-emerald-600" : avgScore >= 50 ? "text-amber-600" : "text-red-600"}`}>
            {avgScore}%
          </p>
          <p className="text-[11px] text-slate-400 mt-1 font-medium">Score index across scans</p>
        </div>
      </div>

      {/* Quick Tools & Legal Metrology Awareness Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/consumer/rules"
          className="card-slate-hover p-5 border-l-4 border-l-emerald-500 flex flex-col justify-between group"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">8 Mandatory Declarations</span>
              <span className="text-base group-hover:translate-x-1 transition-transform">→</span>
            </div>
            <h3 className="text-sm font-extrabold text-slate-900">Legal Metrology Rules, 2011</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Explore MRP rules, net quantity tolerances, consumer care requirements, and manufacturing date formats.
            </p>
          </div>
          <span className="text-xs font-bold text-emerald-600 mt-4 inline-flex items-center gap-1">
            Read Rule Details 📖
          </span>
        </Link>

        <Link
          to="/consumer/compare"
          className="card-slate-hover p-5 border-l-4 border-l-sky-500 flex flex-col justify-between group"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-sky-700">Rule 6 Tool</span>
              <span className="text-base group-hover:translate-x-1 transition-transform">→</span>
            </div>
            <h3 className="text-sm font-extrabold text-slate-900">Unit Sale Price Calculator</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Compare different pack sizes (e.g. 500g vs 1kg) to identify shrinkflation or true price-per-unit cost.
            </p>
          </div>
          <span className="text-xs font-bold text-sky-600 mt-4 inline-flex items-center gap-1">
            Calculate Unit Price ⚖️
          </span>
        </Link>

        <Link
          to="/leaderboard"
          className="card-slate-hover p-5 border-l-4 border-l-purple-500 flex flex-col justify-between group"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-700">Transparency</span>
              <span className="text-base group-hover:translate-x-1 transition-transform">→</span>
            </div>
            <h3 className="text-sm font-extrabold text-slate-900">Brand Compliance Index</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              See how major consumer packaged goods brands rank in adherence to Legal Metrology standards.
            </p>
          </div>
          <span className="text-xs font-bold text-purple-600 mt-4 inline-flex items-center gap-1">
            View Leaderboard 🏆
          </span>
        </Link>
      </div>

      {/* Recent Scans Section */}
      <div className="card-slate p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-extrabold text-slate-900 tracking-tight">Recent Scans</h3>
            <p className="text-xs text-slate-500 mt-0.5">Your latest packaging compliance audits</p>
          </div>
          <Link
            to="/consumer/scans"
            className="text-xs font-bold text-emerald-600 hover:text-emerald-700 hover:underline"
          >
            View All Scans →
          </Link>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading your audit history...</div>
        ) : scans.length === 0 ? (
          <div className="py-12 text-center border-2 border-dashed border-slate-200 rounded-xl">
            <span className="text-3xl">📦</span>
            <p className="text-sm font-bold text-slate-700 mt-2">No product scans yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Capture or upload a photo of any product package (snack, cosmetic, grocery) to audit its mandatory legal declarations.
            </p>
            <Link to="/consumer/scan" className="btn-accent mt-4">
              Scan Your First Product
            </Link>
          </div>
        ) : (
          <div className="space-y-2.5">
            {scans.slice(0, 5).map((scan) => {
              const score = scan.compliance_score || 0;
              const isPassed = score >= 80;
              const isPartial = score >= 50 && score < 80;
              const dateStr = scan.created_at
                ? new Date(scan.created_at).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Recent";

              return (
                <div
                  key={scan.id}
                  onClick={() => setSelectedScan(scan)}
                  className="p-3.5 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 transition-all cursor-pointer flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center font-black text-xs flex-shrink-0 ${
                        isPassed
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          : isPartial
                          ? "bg-amber-100 text-amber-800 border border-amber-200"
                          : "bg-red-100 text-red-800 border border-red-200"
                      }`}
                    >
                      {score}%
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-900 truncate">
                        {getScanTitle(scan)}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">{dateStr}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span
                      className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-md ${
                        isPassed
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : isPartial
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-red-50 text-red-700 border border-red-200"
                      }`}
                    >
                      {isPassed ? "Compliant" : isPartial ? "Attention" : "Violation"}
                    </span>
                    <button
                      type="button"
                      className="p-1 text-slate-400 hover:text-slate-600"
                      title="Inspect scan"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail Drawer for Selected Scan */}
      <AppDrawer
        isOpen={Boolean(selectedScan)}
        onClose={() => setSelectedScan(null)}
        title={selectedScan?.product_name || "Packaging Audit Report"}
        subtitle={`Audit ID: ${selectedScan?.id?.substring(0, 8) || "N/A"}`}
      >
        {selectedScan && (
          <div className="space-y-4">
            <div className="card-slate p-4 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase">Compliance Score</span>
                <p className="text-2xl font-black text-slate-900">{selectedScan.compliance_score || 0} / 100</p>
              </div>
              <span className={`text-xs font-extrabold px-3 py-1 rounded-lg ${
                (selectedScan.compliance_score || 0) >= 80 ? "badge-compliant" : "badge-violation"
              }`}>
                {(selectedScan.compliance_score || 0) >= 80 ? "Pass" : "Non-Compliant"}
              </span>
            </div>

            {selectedScan.extracted_text && (
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">OCR Extracted Text</h4>
                <pre className="p-3 bg-slate-900 text-slate-200 text-[11px] font-mono rounded-xl max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {selectedScan.extracted_text}
                </pre>
              </div>
            )}

            <div className="pt-2">
              <Link
                to="/consumer/scan"
                onClick={() => setSelectedScan(null)}
                className="btn-accent w-full"
              >
                Scan Another Packaging
              </Link>
            </div>
          </div>
        )}
      </AppDrawer>
    </div>
  );
}
