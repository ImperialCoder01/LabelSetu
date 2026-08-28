import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";
import AppDrawer from "../../components/AppDrawer";

export default function MyScansPage() {
  const { user } = useAuth();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [selectedScan, setSelectedScan] = useState(null);

  useEffect(() => {
    async function loadScans() {
      if (!user) return;
      try {
        setLoading(true);
        const { data, error } = await supabase
          .from("scans")
          .select("*")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false });
        if (!error && data) setScans(data);
      } catch (err) {
        console.error("Error fetching scans:", err);
      } finally {
        setLoading(false);
      }
    }
    loadScans();
  }, [user]);

  const filteredScans = useMemo(() => {
    return scans.filter((s) => {
      const matchSearch =
        (s.product_name || "").toLowerCase().includes(search.toLowerCase()) ||
        (s.extracted_text || "").toLowerCase().includes(search.toLowerCase());
      if (!matchSearch) return false;

      const score = s.compliance_score || 0;
      if (filter === "compliant") return score >= 80;
      if (filter === "attention") return score >= 50 && score < 80;
      if (filter === "violation") return score < 50;
      return true;
    });
  }, [scans, search, filter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-900 tracking-tight">My Scans History</h2>
          <p className="text-xs text-slate-500 mt-0.5">All packaging audits verified from your account</p>
        </div>
        <Link to="/consumer/scan" className="btn-accent flex-shrink-0">
          <span>📷</span> Scan New Product
        </Link>
      </div>

      {/* Search & Filters */}
      <div className="card-slate p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <span className="absolute inset-y-0 left-3 flex items-center text-slate-400">🔍</span>
          <input
            type="text"
            placeholder="Search by product name, manufacturer, or keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field pl-9"
          />
        </div>
        <div className="flex gap-2">
          {["all", "compliant", "attention", "violation"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-2 rounded-xl text-xs font-bold capitalize transition-all ${
                filter === f
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Scans Grid / List */}
      {loading ? (
        <div className="py-16 text-center text-xs text-slate-400">Loading your scans...</div>
      ) : filteredScans.length === 0 ? (
        <div className="card-slate py-16 text-center">
          <span className="text-3xl">📋</span>
          <h3 className="text-sm font-bold text-slate-800 mt-2">No matching scans found</h3>
          <p className="text-xs text-slate-400 mt-1">Try adjusting your search query or filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredScans.map((scan) => {
            const score = scan.compliance_score || 0;
            const isPassed = score >= 80;
            const isPartial = score >= 50 && score < 80;
            const dateStr = scan.created_at
              ? new Date(scan.created_at).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })
              : "Recent";

            return (
              <div
                key={scan.id}
                onClick={() => setSelectedScan(scan)}
                className="card-slate-hover p-5 cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
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
                    <span className="text-xs font-mono font-bold text-slate-400">{dateStr}</span>
                  </div>

                  <h3 className="text-sm font-extrabold text-slate-900 line-clamp-1">
                    {scan.product_name || "Packaging Scan"}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                    {scan.extracted_text ? scan.extracted_text.substring(0, 100) + "..." : "No text preview"}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium text-slate-500">Score:</span>
                    <span className={`text-xs font-black ${isPassed ? "text-emerald-600" : "text-red-600"}`}>
                      {score}/100
                    </span>
                  </div>
                  <span className="text-xs font-bold text-emerald-600 hover:underline">
                    Inspect Report →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Drawer */}
      <AppDrawer
        isOpen={Boolean(selectedScan)}
        onClose={() => setSelectedScan(null)}
        title={selectedScan?.product_name || "Packaging Report"}
        subtitle={`Audit ID: ${selectedScan?.id?.substring(0, 8) || "N/A"}`}
      >
        {selectedScan && (
          <div className="space-y-4">
            <div className="card-slate p-4 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase">Overall Compliance</span>
                <p className="text-2xl font-black text-slate-900">{selectedScan.compliance_score || 0} / 100</p>
              </div>
              <span className={`text-xs font-extrabold px-3 py-1 rounded-lg ${
                (selectedScan.compliance_score || 0) >= 80 ? "badge-compliant" : "badge-violation"
              }`}>
                {(selectedScan.compliance_score || 0) >= 80 ? "Compliant" : "Potential Violation"}
              </span>
            </div>

            {selectedScan.extracted_text && (
              <div>
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">OCR Extracted Text</h4>
                <pre className="p-3 bg-slate-900 text-slate-200 text-[11px] font-mono rounded-xl max-h-56 overflow-y-auto whitespace-pre-wrap">
                  {selectedScan.extracted_text}
                </pre>
              </div>
            )}
          </div>
        )}
      </AppDrawer>
    </div>
  );
}
