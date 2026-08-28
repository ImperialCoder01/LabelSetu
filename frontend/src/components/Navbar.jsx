import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTranslation } from "react-i18next";
import LanguageToggle from "./LanguageToggle";

const roleColors = {
  consumer: "bg-sky-100 text-sky-900 border border-sky-300",
  brand: "bg-purple-100 text-purple-900 border border-purple-300",
  regulator: "bg-amber-100 text-amber-900 border border-amber-300",
  admin: "bg-red-100 text-red-900 border border-red-300",
};

export default function Navbar() {
  const { user, profile, role, signOut, switchRole } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleRoleChange = async (e) => {
    const newRole = e.target.value;
    await switchRole(newRole);
    if (newRole === "admin") navigate("/admin");
    else navigate("/dashboard");
  };

  return (
    <nav className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-50 backdrop-blur-md bg-slate-900/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 bg-accent-600 rounded-lg flex items-center justify-center shadow-sm group-hover:bg-accent-500 transition-colors">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white">LabelSetu</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-accent-950 text-accent-400 border border-accent-800">
                  AI Verifier
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5 hidden sm:block">Legal Metrology Compliance Engine</p>
            </div>
          </Link>

          {/* Action Tools & User Profile */}
          <div className="flex items-center gap-4">
            <LanguageToggle />

            {user && (
              <>
                <div className="flex items-center gap-2 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
                  <span className="text-xs text-slate-400 font-medium hidden md:inline">Mode:</span>
                  <select
                    value={role || "consumer"}
                    onChange={handleRoleChange}
                    className={`px-2.5 py-1 rounded-md text-xs font-bold capitalize border-none cursor-pointer focus:ring-2 focus:ring-accent-500 ${
                      roleColors[role] || "bg-slate-700 text-white"
                    }`}
                  >
                    <option value="consumer">Consumer Audit</option>
                    <option value="brand">Brand Compliance SaaS</option>
                    <option value="regulator">Regulator Portal</option>
                    <option value="admin">Admin System ⚙️</option>
                  </select>
                </div>

                {profile?.full_name && (
                  <div className="hidden lg:flex items-center gap-2 text-xs text-slate-300 font-medium pl-2 border-l border-slate-800">
                    <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs">
                      {profile.full_name.charAt(0).toUpperCase()}
                    </div>
                    <span>{profile.full_name}</span>
                  </div>
                )}

                <button
                  onClick={signOut}
                  className="text-xs font-medium text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-slate-800"
                >
                  {t("common.signOut")}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
