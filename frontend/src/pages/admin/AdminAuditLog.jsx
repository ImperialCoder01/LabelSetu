import { useState, useEffect, useMemo, Fragment } from "react";
import { supabase } from "../../lib/supabase";
import { useTranslation } from "react-i18next";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

const ACTION_STYLES = {
  CREATE: "bg-green-100 text-green-800",
  UPDATE: "bg-blue-100 text-blue-800",
  DELETE: "bg-red-100 text-red-800",
};

function JsonDiff({ oldVal, newVal }) {
  const { t } = useTranslation();
  let oldObj = oldVal;
  let newObj = newVal;

  try {
    if (typeof oldVal === "string") oldObj = JSON.parse(oldVal);
  } catch { /* keep raw */ }
  try {
    if (typeof newVal === "string") newObj = JSON.parse(newVal);
  } catch { /* keep raw */ }

  const oldKeys = oldObj && typeof oldObj === "object" ? Object.keys(oldObj) : [];
  const newKeys = newObj && typeof newObj === "object" ? Object.keys(newObj) : [];
  const allKeys = [...new Set([...oldKeys, ...newKeys])];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{t("admin.auditLog.before")}</p>
        {allKeys.length === 0 ? (
          <pre className="text-xs text-gray-600 bg-gray-50 rounded p-2 border border-gray-100 overflow-x-auto max-h-48">
            {typeof oldVal === "object" ? JSON.stringify(oldVal, null, 2) : String(oldVal ?? "—")}
          </pre>
        ) : (
          <div className="space-y-0.5">
            {allKeys.map((key) => {
              const oldStr = oldObj != null && key in (typeof oldObj === "object" ? oldObj : {})
                ? JSON.stringify(oldObj[key])
                : null;
              const newStr = newObj != null && key in (typeof newObj === "object" ? newObj : {})
                ? JSON.stringify(newObj[key])
                : null;
              const changed = oldStr !== newStr;
              return (
                <div key={key} className={"flex items-start gap-2 text-xs px-2 py-1 rounded " + (changed && oldStr != null ? "bg-red-50" : "bg-gray-50")}>
                  <span className="font-mono text-gray-500 shrink-0 w-32 truncate" title={key}>{key}</span>
                  <span className={"font-mono break-all " + (changed && oldStr != null ? "text-red-700 line-through" : "text-gray-700")}>
                    {oldStr ?? <span className="text-gray-400 italic">—</span>}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{t("admin.auditLog.after")}</p>
        {allKeys.length === 0 ? (
          <pre className="text-xs text-gray-600 bg-gray-50 rounded p-2 border border-gray-100 overflow-x-auto max-h-48">
            {typeof newVal === "object" ? JSON.stringify(newVal, null, 2) : String(newVal ?? "—")}
          </pre>
        ) : (
          <div className="space-y-0.5">
            {allKeys.map((key) => {
              const oldStr = oldObj != null && key in (typeof oldObj === "object" ? oldObj : {})
                ? JSON.stringify(oldObj[key])
                : null;
              const newStr = newObj != null && key in (typeof newObj === "object" ? newObj : {})
                ? JSON.stringify(newObj[key])
                : null;
              const changed = oldStr !== newStr;
              return (
                <div key={key} className={"flex items-start gap-2 text-xs px-2 py-1 rounded " + (changed && newStr != null ? "bg-green-50" : "bg-gray-50")}>
                  <span className="font-mono text-gray-500 shrink-0 w-32 truncate" title={key}>{key}</span>
                  <span className={"font-mono break-all " + (changed && newStr != null ? "text-green-700 font-semibold" : "text-gray-700")}>
                    {newStr ?? <span className="text-gray-400 italic">—</span>}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminAuditLog() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => { fetchLogs(); }, [startDate, endDate]);

  async function fetchLogs() {
    setLoading(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) { setLoading(false); return; }
      const params = new URLSearchParams();
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await fetch(`${BACKEND_URL}/api/admin/audit-logs?${params.toString()}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      if (actionFilter !== "all" && log.action_type?.toUpperCase() !== actionFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const name = (log.users_profile?.full_name || "").toLowerCase();
        const table = (log.target_table || "").toLowerCase();
        const targetId = String(log.target_id || "").toLowerCase();
        const action = (log.action_type || "").toLowerCase();
        if (!name.includes(q) && !table.includes(q) && !targetId.includes(q) && !action.includes(q)) return false;
      }
      return true;
    });
  }, [logs, actionFilter, search]);

  const actionCounts = useMemo(() => ({
    all: logs.length,
    CREATE: logs.filter((l) => l.action_type?.toUpperCase() === "CREATE").length,
    UPDATE: logs.filter((l) => l.action_type?.toUpperCase() === "UPDATE").length,
    DELETE: logs.filter((l) => l.action_type?.toUpperCase() === "DELETE").length,
  }), [logs]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("admin.auditLog.title")}</h1>
        <p className="text-gray-500 mt-1">{t("admin.auditLog.subtitle")}</p>
      </div>

      <div className="card">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              type="text"
              placeholder={t("admin.auditLog.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex gap-1.5">
            {["all", "CREATE", "UPDATE", "DELETE"].map((f) => (
              <button
                key={f}
                onClick={() => setActionFilter(f)}
                className={
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors " +
                  (actionFilter === f
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200")
                }
              >
                {f === "all" ? t("admin.auditLog.allActions") : f}
                {actionCounts[f] > 0 && (
                  <span
                    className={
                      "ml-1 inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full " +
                      (actionFilter === f ? "bg-white/20 text-white" : "bg-gray-200 text-gray-700")
                    }
                  >
                    {actionCounts[f]}
                  </span>
                )}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
            {(startDate || endDate) && (
              <button onClick={() => { setStartDate(""); setEndDate(""); }} className="text-xs text-gray-500 hover:text-red-600 underline">
                {t("admin.auditLog.clear")}
              </button>
            )}
          </div>
          <span className="text-xs text-gray-400 ml-auto">{t("admin.auditLog.entries", { count: filtered.length })}</span>
        </div>
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
            <span className="ml-3 text-sm text-gray-500">{t("common.loading")}</span>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-center py-8">{t("admin.auditLog.noEntries")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left">
                  <th className="py-3 px-3 w-8" />
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.timestamp")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.admin")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.action")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.table")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.targetId")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.auditLog.details")}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((log) => {
                  const isExpanded = expandedId === log.id;
                  const hasDetails = log.old_value || log.new_value;
                  const style = ACTION_STYLES[log.action_type?.toUpperCase()] || "bg-gray-100 text-gray-700";
                  return (
                    <Fragment key={log.id}>
                      <tr
                        className={"border-b border-gray-50 transition-colors " + (hasDetails ? "cursor-pointer hover:bg-gray-50" : "")}
                        onClick={() => hasDetails && setExpandedId(isExpanded ? null : log.id)}
                      >
                        <td className="py-3 px-3 text-center">
                          {hasDetails ? (
                            <svg className={"w-4 h-4 text-gray-400 transition-transform " + (isExpanded ? "rotate-90" : "")} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                            </svg>
                          ) : (
                            <span className="block w-4" />
                          )}
                        </td>
                        <td className="py-3 px-3 text-gray-500 text-xs whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                        <td className="py-3 px-3 text-gray-900 text-sm">{log.users_profile?.full_name || "System"}</td>
                        <td className="py-3 px-3"><span className={"px-2 py-0.5 rounded text-xs font-bold " + style}>{log.action_type}</span></td>
                        <td className="py-3 px-3 font-mono text-gray-600 text-xs">{log.target_table}</td>
                        <td className="py-3 px-3 font-mono text-gray-400 text-xs" title={log.target_id || ""}>{log.target_id ? String(log.target_id).substring(0, 8) + "…" : "—"}</td>
                        <td className="py-3 px-3 text-gray-500 text-xs">{hasDetails ? t("admin.auditLog.clickToExpand") : "—"}</td>
                      </tr>
                      {isExpanded && (
                        <tr className="border-b border-gray-100 bg-gray-50/50">
                          <td colSpan={7} className="px-4 py-4">
                            <JsonDiff oldVal={log.old_value} newVal={log.new_value} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
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
