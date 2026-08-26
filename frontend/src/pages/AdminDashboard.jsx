import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { supabase } from "../lib/supabase";
import { useTranslation } from "react-i18next";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const COLORS = {
  primary: "#2563eb",
  green: "#16a34a",
  amber: "#d97706",
  red: "#dc2626",
  purple: "#9333ea",
  grid: "#e5e7eb",
  text: "#6b7280",
};

const DATE_RANGES = [
  { key: "7d", label: "7 Days", days: 7 },
  { key: "30d", label: "30 Days", days: 30 },
  { key: "month", label: "This Month", days: null },
  { key: "all", label: "All Time", days: null },
];

const REFRESH_INTERVAL = 30000; // 30 seconds

function StatCard({ label, value, sub, color = "text-gray-900", icon }) {
  return (
    <div className="card group hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        {icon && (
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${icon.bg}`}>
            <svg className={`w-5 h-5 ${icon.color}`} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d={icon.path} />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 bg-gray-200 rounded animate-pulse w-64" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 bg-gray-200 rounded-xl animate-pulse" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-80 bg-gray-200 rounded-xl animate-pulse" />
        <div className="h-80 bg-gray-200 rounded-xl animate-pulse" />
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const { t } = useTranslation();
  const [scans, setScans] = useState([]);
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState("30d");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef(null);

  const fetchAll = useCallback(async () => {
    const [scansRes, usersRes, logsRes] = await Promise.all([
      supabase.from("scans").select("id, compliance_score, missing_fields, created_at, user_id, users_profile!scans_user_id_fkey(full_name, role)"),
      supabase.from("users_profile").select("id, role, created_at"),
      supabase.from("audit_log").select("*, users_profile!audit_log_admin_id_fkey(full_name)").order("timestamp", { ascending: false }).limit(15),
    ]);
    if (!scansRes.error) setScans(scansRes.data || []);
    if (!usersRes.error) setUsers(usersRes.data || []);
    if (!logsRes.error) setAuditLogs(logsRes.data || []);
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ─── Auto-refresh ────────────────────────────────────────────────────
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchAll, REFRESH_INTERVAL);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, fetchAll]);

  // ─── Date range filtering ─────────────────────────────────────────────
  const filteredScans = useMemo(() => {
    const range = DATE_RANGES.find((r) => r.key === dateRange);
    if (!range || range.key === "all") return scans;
    if (range.key === "month") {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
      return scans.filter((s) => s.created_at >= start);
    }
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - range.days);
    const iso = cutoff.toISOString();
    return scans.filter((s) => s.created_at >= iso);
  }, [scans, dateRange]);

  // ─── Derived stats (filtered) ─────────────────────────────────────────
  const stats = useMemo(() => {
    const brandCount = users.filter((u) => u.role === "brand").length;
    const avgScore = filteredScans.length > 0
      ? Math.round(filteredScans.reduce((a, s) => a + (s.compliance_score || 0), 0) / filteredScans.length)
      : 0;
    const flagged = filteredScans.filter((s) => s.compliance_score < 50).length;
    return { totalScans: filteredScans.length, brandCount, avgScore, flagged };
  }, [filteredScans, users]);

  // ─── Scans-per-day data (date-range aware) ───────────────────────────
  const scansPerDay = useMemo(() => {
    const range = DATE_RANGES.find((r) => r.key === dateRange);
    const now = new Date();
    const numDays = range?.days || (range?.key === "month" ? now.getDate() : 30);
    const days = {};
    for (let i = numDays - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      days[d.toISOString().slice(0, 10)] = 0;
    }
    filteredScans.forEach((s) => {
      const key = s.created_at?.slice(0, 10);
      if (key && key in days) days[key]++;
    });
    return Object.entries(days).map(([date, count]) => ({
      date: date.slice(5),
      count,
    }));
  }, [filteredScans, dateRange]);

  // ─── Most-failed fields data (filtered) ──────────────────────────────
  const failedFields = useMemo(() => {
    const counts = {};
    filteredScans.forEach((s) => {
      if (Array.isArray(s.missing_fields)) {
        s.missing_fields.forEach((f) => {
          const name = typeof f === "string" ? f : f.name || f.id || String(f);
          counts[name] = (counts[name] || 0) + 1;
        });
      }
    });
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [filteredScans]);

  // ─── Brand breakdown ─────────────────────────────────────────────────
  const brandBreakdown = useMemo(() => {
    const brands = {};
    filteredScans.forEach((s) => {
      const name = s.users_profile?.full_name || "Unknown";
      if (s.users_profile?.role !== "brand") return;
      if (!brands[name]) brands[name] = { name, scans: 0, totalScore: 0 };
      brands[name].scans++;
      brands[name].totalScore += s.compliance_score || 0;
    });
    return Object.values(brands)
      .map((b) => ({ ...b, avgScore: b.scans > 0 ? Math.round(b.totalScore / b.scans) : 0 }))
      .sort((a, b) => b.scans - a.scans)
      .slice(0, 8);
  }, [filteredScans]);

  if (loading) return <Skeleton />;

  const rangeLabel = DATE_RANGES.find((r) => r.key === dateRange)?.label || "";

  return (
    <div className="space-y-8">
      {/* ─── Header + Controls ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("admin.dashboard.title")}</h1>
          <p className="text-gray-500 mt-1">{t("admin.dashboard.subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              autoRefresh
                ? "bg-green-50 border-green-200 text-green-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${autoRefresh ? "bg-green-500 animate-pulse" : "bg-gray-300"}`} />
            {autoRefresh ? t("admin.dashboard.autoRefreshOn") : t("admin.dashboard.autoRefreshOff")}
          </button>

          {/* Date range pills */}
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {DATE_RANGES.map((r) => (
              <button
                key={r.key}
                onClick={() => setDateRange(r.key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  dateRange === r.key
                    ? "bg-white text-primary-700 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Summary Cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label={t("admin.dashboard.totalScans")}
          value={stats.totalScans.toLocaleString()}
          sub={rangeLabel}
          color="text-primary-600"
          icon={{ bg: "bg-primary-50", color: "text-primary-600", path: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" }}
        />
        <StatCard
          label={t("admin.dashboard.totalBrands")}
          value={stats.brandCount}
          sub={`${users.length} total users`}
          color="text-purple-600"
          icon={{ bg: "bg-purple-50", color: "text-purple-600", path: "M13.5 21v-7.5a.75.75 0 01.75-.75h3a.75.75 0 01.75.75V21m-4.5 0H2.36m11.14 0H18m0 0h3.64m-1.39 0V9.349m-16.5 11.65V9.35m0 0a3.001 3.001 0 003.75-.615A2.993 2.993 0 009.75 9.75c.896 0 1.7-.393 2.25-1.016a2.993 2.993 0 002.25 1.016c.896 0 1.7-.393 2.25-1.016A3.001 3.001 0 0021 9.349" }}
        />
        <StatCard
          label={t("admin.dashboard.avgCompliance")}
          value={`${stats.avgScore}%`}
          sub={stats.avgScore >= 80 ? "Healthy" : stats.avgScore >= 50 ? "Needs attention" : "Critical"}
          color={stats.avgScore >= 80 ? "text-green-600" : stats.avgScore >= 50 ? "text-amber-600" : "text-red-600"}
          icon={{ bg: stats.avgScore >= 80 ? "bg-green-50" : stats.avgScore >= 50 ? "bg-amber-50" : "bg-red-50", color: stats.avgScore >= 80 ? "text-green-600" : stats.avgScore >= 50 ? "text-amber-600" : "text-red-600", path: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" }}
        />
        <StatCard
          label={t("admin.dashboard.flaggedReports")}
          value={stats.flagged}
          sub={stats.totalScans > 0 ? `${Math.round((stats.flagged / stats.totalScans) * 100)}% of scans` : "0% of scans"}
          color="text-red-600"
          icon={{ bg: "bg-red-50", color: "text-red-600", path: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" }}
        />
      </div>

      {/* ─── Charts Row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Line Chart — Scans per Day */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Scans per Day ({rangeLabel})</h2>
          {filteredScans.length === 0 ? (
            <p className="text-gray-400 text-sm py-12 text-center">No scan data for this period.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={scansPerDay} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: COLORS.text }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: COLORS.text }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} labelStyle={{ fontWeight: 600 }} />
                <Line type="monotone" dataKey="count" stroke={COLORS.primary} strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: COLORS.primary }} name="Scans" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bar Chart — Most Failed Fields */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Most Failed Fields ({rangeLabel})</h2>
          {failedFields.length === 0 ? (
            <p className="text-gray-400 text-sm py-12 text-center">No missing field data for this period.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={failedFields} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: COLORS.text }} tickLine={false} />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: COLORS.text }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} labelStyle={{ fontWeight: 600 }} formatter={(value) => [`${value} scans`, "Failures"]} />
                <Bar dataKey="count" name="Failures" radius={[0, 4, 4, 0]}>
                  {failedFields.map((_, i) => (<Cell key={i} fill={i < 3 ? COLORS.red : COLORS.amber} />))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ─── Brand Breakdown ───────────────────────────────────────────── */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Brand Breakdown ({rangeLabel})</h2>
        {brandBreakdown.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No brand scan data for this period.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 px-3 font-medium text-gray-500">Brand</th>
                  <th className="py-2 px-3 font-medium text-gray-500 text-right">Scans</th>
                  <th className="py-2 px-3 font-medium text-gray-500 text-right">Avg. Score</th>
                  <th className="py-2 px-3 font-medium text-gray-500">Compliance</th>
                </tr>
              </thead>
              <tbody>
                {brandBreakdown.map((b) => (
                  <tr key={b.name} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-3 font-medium text-gray-900">{b.name}</td>
                    <td className="py-3 px-3 text-right text-gray-700">{b.scans}</td>
                    <td className="py-3 px-3 text-right font-semibold" style={{ color: b.avgScore >= 80 ? COLORS.green : b.avgScore >= 50 ? COLORS.amber : COLORS.red }}>
                      {b.avgScore}%
                    </td>
                    <td className="py-3 px-3 w-48">
                      <div className="bg-gray-100 rounded-full h-2.5 overflow-hidden">
                        <div className="h-2.5 rounded-full transition-all duration-500" style={{ width: `${b.avgScore}%`, backgroundColor: b.avgScore >= 80 ? COLORS.green : b.avgScore >= 50 ? COLORS.amber : COLORS.red }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ─── Bottom Row: Recent Activity + Audit Log ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Scans */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Recent Scans</h2>
          {filteredScans.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No scans yet.</p>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {filteredScans.slice(0, 10).map((s) => {
                const score = s.compliance_score || 0;
                const badge = score >= 80 ? "bg-green-100 text-green-800" : score >= 50 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800";
                return (
                  <div key={s.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold ${badge}`}>{score}</div>
                      <div className="min-w-0">
                        <p className="text-sm text-gray-900 truncate">{s.users_profile?.full_name || `Scan #${s.id.substring(0, 8)}`}</p>
                        <p className="text-xs text-gray-500">{new Date(s.created_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${badge}`}>
                      {score >= 80 ? "Pass" : score >= 50 ? "Partial" : "Fail"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Audit Logs */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Recent Activity</h2>
          {auditLogs.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No activity yet.</p>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {auditLogs.map((log) => (
                <div key={log.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-start">
                    <span className="text-sm font-medium text-gray-900">{log.action_type}</span>
                    <span className="text-xs text-gray-400 whitespace-nowrap ml-2">{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {log.users_profile?.full_name || "System"} &rarr; {log.target_table}
                    {log.target_id ? ` #${String(log.target_id).substring(0, 8)}` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
