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

        const res = await fetch(`${BACKEND_URL}/api/ocr/usage`, {
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
          <h1 className="text-2xl font-bold text-gray-900">{t("admin.apiUsage.title")}</h1>
          <p className="text-gray-500 mt-1">{t("admin.apiUsage.subtitle")}</p>
        </div>
        <div className="card flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          <span className="ml-3 text-gray-500">{t("admin.apiUsage.loadingData")}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("admin.apiUsage.title")}</h1>
          <p className="text-gray-500 mt-1">{t("admin.apiUsage.subtitle")}</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
            <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <p className="text-sm font-medium text-red-800">Failed to load usage data: {error}</p>
          </div>
        </div>
      </div>
    );
  }

  const { provider, request_count, quota_limit, usage_percent, warning } = data;
  const isCloud = provider === "cloud";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Usage</h1>
        <p className="text-gray-500 mt-1">Monitor API quota and provider usage</p>
      </div>

      {isCloud ? (
        <>
          {/* Cloud provider — progress bar */}
          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-sm font-medium text-gray-500">{t("admin.apiUsage.provider")}</p>
                <p className="text-lg font-bold text-gray-900">{t("admin.apiUsage.cloudProvider")}</p>
              </div>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700">
                Cloud
              </span>
            </div>

            {/* Warning banner */}
            {warning && (
              <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-50 border border-red-200">
                <svg
                  className="w-5 h-5 text-red-600 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
                  />
                </svg>
                <p className="text-sm font-medium text-red-800">
                  Warning — Usage has exceeded 80% of your monthly quota.
                  Consider switching to local OCR to avoid overage.
                </p>
              </div>
            )}

            {/* Progress bar */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">
                  {t("admin.apiUsage.requestsUsed", { used: request_count.toLocaleString(), limit: quota_limit.toLocaleString() })}
                </span>
                <span
                  className={`text-sm font-semibold ${
                    warning ? "text-red-600" : "text-gray-600"
                  }`}
                >
                  {usage_percent.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    warning ? "bg-red-500" : "bg-primary-500"
                  }`}
                  style={{ width: `${Math.min(usage_percent, 100)}%` }}
                />
              </div>
            </div>

            <p className="mt-3 text-sm text-gray-500">
              {t("admin.apiUsage.remainingRequests", { count: (quota_limit - request_count).toLocaleString() })}
            </p>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <p className="text-sm text-gray-500">{t("admin.apiUsage.requestsUsed2")}</p>
              <p className="text-3xl font-bold text-primary-600 mt-1">
                {request_count.toLocaleString()}
              </p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">{t("admin.apiUsage.quotaLimit")}</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {quota_limit.toLocaleString()}
              </p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">{t("admin.apiUsage.remaining")}</p>
              <p
                className={`text-3xl font-bold mt-1 ${
                  warning ? "text-red-600" : "text-green-600"
                }`}
              >
                {Math.max(quota_limit - request_count, 0).toLocaleString()}
              </p>
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Local provider — badge */}
          <div className="card">
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-1">
                {t("admin.apiUsage.localBadge")}
              </h2>
              <p className="text-gray-500 max-w-md">
                {t("admin.apiUsage.localDesc")}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card">
              <p className="text-sm text-gray-500">{t("admin.apiUsage.provider")}</p>
              <p className="text-lg font-bold text-green-600 mt-1">{t("admin.apiUsage.localProvider")}</p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">{t("admin.apiUsage.monthlyRequests")}</p>
              <p className="text-lg font-bold text-gray-900 mt-1">
                {t("admin.apiUsage.logged", { count: request_count.toLocaleString() })}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
