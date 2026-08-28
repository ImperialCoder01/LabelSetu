import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";
import { useTranslation } from "react-i18next";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

const STATUS_STYLES = {
  pending: { bg: "bg-yellow-100", text: "text-yellow-800", label: "Pending" },
  forwarded: { bg: "bg-blue-100", text: "text-blue-800", label: "Forwarded" },
  resolved: { bg: "bg-green-100", text: "text-green-800", label: "Resolved" },
  spam: { bg: "bg-gray-100", text: "text-gray-600", label: "Spam" },
};

export default function AdminReports() {
  const { t } = useTranslation();
  const [scans, setScans] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    const [{ data: scanData }, { data: reportData }] = await Promise.all([
      supabase
        .from("scans")
        .select("*, users_profile!scans_user_id_fkey(full_name, role)")
        .order("created_at", { ascending: false }),
      fetchReports(),
    ]);
    if (scanData) setScans(scanData);
    if (reportData) setReports(reportData);
    setLoading(false);
  }

  async function fetchReports() {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return [];
      const res = await fetch(`${BACKEND_URL}/api/reports`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }

  async function updateReportStatus(reportId, action) {
    setActionLoading(reportId);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const res = await fetch(`${BACKEND_URL}/api/reports/${reportId}/${action}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        setReports((prev) =>
          prev.map((r) =>
            r.id === reportId
              ? { ...r, status: action === "forward" ? "forwarded" : action === "resolve" ? "resolved" : "spam" }
              : r
          )
        );
      }
    } catch (err) {
      console.error("Action failed:", err);
    } finally {
      setActionLoading(null);
    }
  }

  const filteredReports = reports.filter(
    (r) => filter === "all" || r.status === filter
  );

  const total = scans.length;
  const avg =
    total > 0
      ? Math.round(scans.reduce((a, s) => a + (s.compliance_score || 0), 0) / total)
      : 0;
  const compliant = scans.filter((s) => s.compliance_score >= 80).length;
  const partial = scans.filter(
    (s) => s.compliance_score >= 50 && s.compliance_score < 80
  ).length;
  const nonCompliant = scans.filter((s) => s.compliance_score < 50).length;
  const passRate = total > 0 ? Math.round((compliant / total) * 100) : 0;

  const reportCounts = {
    all: reports.length,
    pending: reports.filter((r) => r.status === "pending").length,
    forwarded: reports.filter((r) => r.status === "forwarded").length,
    resolved: reports.filter((r) => r.status === "resolved").length,
    spam: reports.filter((r) => r.status === "spam").length,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("admin.reports.title")}</h1>
        <p className="text-gray-500 mt-1">
          {t("admin.reports.subtitle")}
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="card text-center p-6">
          <p className="text-5xl font-bold text-gray-900">{total}</p>
          <p className="text-sm text-gray-500 mt-1">{t("admin.reports.totalScans")}</p>
        </div>
        <div className="card text-center p-6">
          <p
            className={
              "text-5xl font-bold " +
              (avg >= 80
                ? "text-green-600"
                : avg >= 50
                ? "text-yellow-600"
                : "text-red-600")
            }
          >
            {avg}%
          </p>
          <p className="text-sm text-gray-500 mt-1">{t("admin.reports.avgScore")}</p>
        </div>
        <div className="card text-center p-6">
          <p className="text-5xl font-bold text-blue-600">{passRate}%</p>
          <p className="text-sm text-gray-500 mt-1">{t("admin.reports.passRate")}</p>
        </div>
        <div className="card text-center p-6">
          <p className="text-5xl font-bold text-yellow-600">{reportCounts.pending}</p>
          <p className="text-sm text-gray-500 mt-1">{t("admin.reports.pendingReports")}</p>
        </div>
        <div className="card text-center p-6">
          <p className="text-5xl font-bold text-red-600">{reportCounts.forwarded}</p>
          <p className="text-sm text-gray-500 mt-1">{t("admin.reports.forwarded")}</p>
        </div>
      </div>

      {/* Score distribution */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">
          Score Distribution
        </h2>
        <div className="space-y-3">
          {[
            { label: "Compliant (80-100)", count: compliant, color: "bg-green-500", textColor: "text-green-700" },
            { label: "Partial (50-79)", count: partial, color: "bg-yellow-500", textColor: "text-yellow-700" },
            { label: "Non-Compliant (<50)", count: nonCompliant, color: "bg-red-500", textColor: "text-red-700" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-4">
              <span className={"text-sm w-44 " + item.textColor}>{item.label}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                <div
                  className={item.color + " h-6 rounded-full transition-all duration-500"}
                  style={{ width: total > 0 ? (item.count / total) * 100 + "%" : "0%" }}
                />
              </div>
              <span className="text-sm font-semibold text-gray-700 w-12 text-right">
                {item.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Report queue */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            {t("admin.reports.reportQueue")}
          </h2>
          <div className="flex gap-1.5">
            {["all", "pending", "forwarded", "resolved", "spam"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors " +
                  (filter === f
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200")
                }
              >
                {f === "all" ? "All" : STATUS_STYLES[f].label}
                {reportCounts[f] > 0 && (
                  <span
                    className={
                      "ml-1.5 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full " +
                      (filter === f ? "bg-white/20 text-white" : "bg-gray-200 text-gray-700")
                    }
                  >
                    {reportCounts[f]}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : filteredReports.length === 0 ? (
          <p className="text-gray-500">No reports match the current filter.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.date")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.reporter")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.brandProduct")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.score")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.reason")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500">{t("admin.reports.status")}</th>
                  <th className="py-3 px-3 font-medium text-gray-500 text-right">{t("admin.reports.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredReports.map((report) => {
                  const scan = report.scans;
                  const reporter = report.users_profile;
                  const statusStyle = STATUS_STYLES[report.status] || STATUS_STYLES.pending;
                  return (
                    <tr
                      key={report.id}
                      className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(report.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-3 text-gray-900 text-sm">
                        {reporter?.full_name || "Unknown"}
                      </td>
                      <td className="py-3 px-3">
                        <p className="text-gray-900 text-sm truncate max-w-[200px]">
                          {scan?.extracted_text?.substring(0, 50) || "—"}
                        </p>
                        <p className="text-xs text-gray-400 capitalize">
                          {scan?.users_profile?.full_name || "—"}
                        </p>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={
                            "font-bold text-sm " +
                            (scan?.compliance_score >= 80
                              ? "text-green-600"
                              : scan?.compliance_score >= 50
                              ? "text-yellow-600"
                              : "text-red-600")
                          }
                        >
                          {scan?.compliance_score ?? "—"}%
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-600 text-xs max-w-[150px] truncate">
                        {report.reason || "—"}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={
                            "px-2 py-0.5 rounded text-xs font-medium " +
                            statusStyle.bg + " " + statusStyle.text
                          }
                        >
                          {statusStyle.label}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        {report.status === "pending" && (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => updateReportStatus(report.id, "forward")}
                              disabled={actionLoading === report.id}
                              className="px-2.5 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors disabled:opacity-50"
                              title="Forward to Regulator"
                            >
                              {t("admin.reports.forward")}
                            </button>
                            <button
                              onClick={() => updateReportStatus(report.id, "resolve")}
                              disabled={actionLoading === report.id}
                              className="px-2.5 py-1 rounded text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors disabled:opacity-50"
                              title="Mark Resolved"
                            >
                              {t("admin.reports.resolve")}
                            </button>
                            <button
                              onClick={() => updateReportStatus(report.id, "dismiss")}
                              disabled={actionLoading === report.id}
                              className="px-2.5 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200 transition-colors disabled:opacity-50"
                              title="Dismiss as Spam"
                            >
                              {t("admin.reports.dismissSpam")}
                            </button>
                          </div>
                        )}
                        {report.status === "forwarded" && (
                          <span className="text-xs text-blue-600">{t("admin.reports.awaitingRegulator")}</span>
                        )}
                        {report.status === "resolved" && (
                          <span className="text-xs text-green-600">{t("admin.reports.completed")}</span>
                        )}
                        {report.status === "spam" && (
                          <span className="text-xs text-gray-400">{t("admin.reports.dismissed")}</span>
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
