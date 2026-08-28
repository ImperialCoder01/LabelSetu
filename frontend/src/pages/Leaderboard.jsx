import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

const MEDAL_COLORS = [
  "bg-yellow-400 text-yellow-900",
  "bg-gray-300 text-gray-700",
  "bg-amber-600 text-amber-100",
];

function scoreColor(score) {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

export default function Leaderboard() {
  const { t } = useTranslation();
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/leaderboard`)
      .then((res) => res.json())
      .then((data) => setBrands(data))
      .catch((err) => console.error("Failed to load leaderboard:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between h-14 items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">L</span>
            </div>
            <span className="text-lg font-bold text-gray-900">LabelSetu</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-gray-600 hover:text-primary-600 transition-colors">
              {t("common.signIn")}
            </Link>
            <Link to="/signup" className="text-sm px-3 py-1.5 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors">
              {t("nav.getStarted")}
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 mb-4">
            <svg className="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.996.176-1.734.86-1.734 1.814v11.214c0 .954.738 1.638 1.734 1.814m10.5-8.118c.996.176 1.734.86 1.734 1.814v11.214c0 .954-.738 1.638-1.734 1.814M10.5 4.236v2.688M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{t("leaderboard.title")}</h1>
          <p className="text-gray-500 max-w-lg mx-auto">
            {t("leaderboard.subtitle")}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
              <span className="ml-3 text-gray-500">{t("common.loading")}</span>
            </div>
          ) : brands.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-gray-500">{t("leaderboard.noData")}</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide w-12">
                    {t("leaderboard.rank")}
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {t("leaderboard.brand")}
                  </th>
                  <th className="py-3 px-4 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide w-20">
                    {t("leaderboard.scans")}
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide w-32">
                    {t("leaderboard.avgScore")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {brands.map((brand, i) => (
                  <tr
                    key={brand.user_id}
                    className={
                      "border-b border-gray-50 transition-colors hover:bg-gray-50 " +
                      (i < 3 ? "bg-primary-50/30" : "")
                    }
                  >
                    <td className="py-4 px-4">
                      {i < 3 ? (
                        <span className={"inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold " + MEDAL_COLORS[i]}>
                          {i + 1}
                        </span>
                      ) : (
                        <span className="text-sm font-medium text-gray-400 ml-2">
                          {i + 1}
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-primary-700 font-semibold text-sm">
                            {brand.brand_name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span className="text-sm font-semibold text-gray-900">
                          {brand.brand_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <span className="text-sm text-gray-600">{brand.scan_count}</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div
                            className={
                              "h-full rounded-full transition-all duration-700 " +
                              (brand.average_score >= 80
                                ? "bg-green-500"
                                : brand.average_score >= 50
                                ? "bg-yellow-500"
                                : "bg-red-500")
                            }
                            style={{ width: brand.average_score + "%" }}
                          />
                        </div>
                        <span className={"text-sm font-bold w-12 text-right " + scoreColor(brand.average_score)}>
                          {brand.average_score}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          {t("leaderboard.realTime")}
        </p>
      </main>
    </div>
  );
}
