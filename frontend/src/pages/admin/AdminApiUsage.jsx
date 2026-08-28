import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";
import { useTranslation } from "react-i18next";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

export default function AdminApiUsage() {
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) {
          setError("Not authenticated");
          setLoading(false);
          return;
        }

        const res = await fetch(`${BACKEND_URL}/api/usage`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });

        if (!res.ok) {
          throw new Error(`API returned ${res.status}`);
        }

        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to load API usage:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-black text-slate-900 tracking-tight">API Usage & Telemetry</h2>
          <p className="text-xs text-slate-500 mt-0.5">Monitor API quota limits, provider allocation, and request metrics</p>
        </div>
        <div className="card-slate flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-3 border-slate-300 border-t-emerald-600" />
          <span className="ml-3 text-xs font-bold text-slate-500">Loading API usage metrics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-black text-slate-900 tracking-tight">API Usage & Telemetry</h2>
          <p className="text-xs text-slate-500 mt-0.5">Monitor API quota limits, provider allocation, and request metrics</p>
        </div>
        <div className="card-slate p-6">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900">
            <span className="text-xl">⚠️</span>
            <p className="text-xs font-bold">Failed to load usage data: {error}</p>
          </div>
        </div>
      </div>
    );
  }

  const { provider, request_count = 0, quota_limit = 25000, usage_percent = 0, warning = false, month = "", groq_available = true, groq_model = "openai/gpt-oss-20b", external_research_enabled = true } = data || {};
  const isCloud = provider === "cloud";

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-black text-slate-900 tracking-tight">API Usage & Telemetry</h2>
        <p className="text-xs text-slate-500 mt-0.5">Monitor active OCR engine quota, monthly volume, and rate telemetry</p>
      </div>

      {isCloud ? (
        <>
          {/* Cloud Provider Quota Card */}
          <div className="card-slate p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Engine</p>
                <p className="text-base font-extrabold text-slate-900 mt-0.5">Cloud OCR Engine (OCR.space Tier)</p>
              </div>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-extrabold bg-sky-50 text-sky-700 border border-sky-200">
                Cloud Provider ({month})
              </span>
            </div>

            {/* Warning Banner if quota > 80% */}
            {warning && (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs">
                <span className="text-lg">⚠️</span>
                <p className="font-medium">
                  <strong>Quota Warning:</strong> Monthly request volume has exceeded 80% of allocation. Consider upgrading your API allocation to prevent request rate throttling.
                </p>
              </div>
            )}

            {/* Progress bar */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>
                  Requests Utilized: <span className="font-mono text-slate-900">{request_count.toLocaleString()}</span> / {quota_limit.toLocaleString()}
                </span>
                <span className={`font-mono ${warning ? "text-red-600 font-extrabold" : "text-slate-600"}`}>
                  {usage_percent.toFixed(2)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    warning ? "bg-red-500" : "bg-emerald-600"
                  }`}
                  style={{ width: `${Math.min(usage_percent, 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Remaining Monthly Allocation: <span className="font-bold text-slate-700 font-mono">{Math.max(quota_limit - request_count, 0).toLocaleString()} requests</span>
              </p>
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card-slate p-5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Requests Logged</span>
              <p className="text-3xl font-black text-slate-900 mt-1 font-mono">{request_count.toLocaleString()}</p>
              <p className="text-[11px] text-slate-400 mt-1">Billing cycle: {month || "Current"}</p>
            </div>

            <div className="card-slate p-5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Monthly Quota</span>
              <p className="text-3xl font-black text-slate-900 mt-1 font-mono">{quota_limit.toLocaleString()}</p>
              <p className="text-[11px] text-slate-400 mt-1">Tier: Free Tier Allocation</p>
            </div>

            <div className="card-slate p-5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Available Capacity</span>
              <p className={`text-3xl font-black mt-1 font-mono ${warning ? "text-red-600" : "text-emerald-600"}`}>
                {Math.max(quota_limit - request_count, 0).toLocaleString()}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Resets 1st of next month</p>
            </div>
          </div>

          {/* Groq AI Status Card */}
          <div className="card-slate p-6 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-base shadow-xs">
                  🤖
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-slate-900">Groq AI Inference Engine</h3>
                  <p className="text-xs text-slate-500">Semantic interpretation & packaging recommendation pipeline</p>
                </div>
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-extrabold ${
                groq_available ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}>
                {groq_available ? "ONLINE / ACTIVE" : "OFFLINE / UNCONFIGURED"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] block">Active Model</span>
                <span className="font-bold text-slate-800 font-mono mt-0.5 block">{groq_model}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] block">Role in Pipeline</span>
                <span className="font-bold text-slate-800 mt-0.5 block">Supplementary Semantics & Recommendations (Non-Blocking)</span>
              </div>
            </div>
          </div>

          {/* External Product Research Engine Card */}
          <div className="card-slate p-6 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center font-bold text-base shadow-xs">
                  🌐
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-slate-900">External Product Research Engine</h3>
                  <p className="text-xs text-slate-500">Public GTIN catalog & Open Food Facts cross-referencing</p>
                </div>
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-extrabold ${
                external_research_enabled ? "bg-sky-50 text-sky-700 border border-sky-200" : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}>
                {external_research_enabled ? "ACTIVE (OFFICIAL & PUBLIC CATALOGS)" : "DISABLED"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] block">Authoritative Sources</span>
                <span className="font-bold text-slate-800 mt-0.5 block">National FMCG Catalog & Open Food Facts Database</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] block">Legal Safety Contract</span>
                <span className="font-bold text-slate-800 mt-0.5 block">Evidence Segregated (Never overrides physical package rule score)</span>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Local Provider View */}
          <div className="card-slate p-8 text-center space-y-3">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto text-2xl shadow-xs">
              🛡️
            </div>
            <h3 className="text-base font-extrabold text-slate-900">Local OCR Engine Active</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              Optical character recognition runs entirely on server compute using OCR cloud service. No external API quotas or third-party usage limits apply.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="card-slate p-5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Engine</span>
              <p className="text-lg font-black text-emerald-600 mt-1">Cloud OCR.space</p>
            </div>
            <div className="card-slate p-5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Requests Processed</span>
              <p className="text-lg font-black text-slate-900 mt-1 font-mono">{request_count.toLocaleString()} calls</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
