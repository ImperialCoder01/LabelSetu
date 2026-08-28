import { useAuth } from "../context/AuthContext";
import LanguageToggle from "./LanguageToggle";
import { Link, useNavigate, useLocation } from "react-router-dom";

export default function AppHeader({ onToggleMobileMenu, title, subtitle, breadcrumbs = [] }) {
  const { profile, role, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const userRole = role || "consumer";

  const firstName = profile?.full_name
    ? profile.full_name.trim().split(" ")[0]
    : "User";

  const roleStyles = {
    consumer: "bg-sky-50 text-sky-800 border-sky-200",
    brand: "bg-purple-50 text-purple-800 border-purple-200",
    regulator: "bg-amber-50 text-amber-800 border-amber-200",
    admin: "bg-red-50 text-red-800 border-red-200",
  };

  const handleAdminViewChange = (e) => {
    const target = e.target.value;
    if (target === "admin") navigate("/admin");
    else if (target === "brand") navigate("/brand");
    else if (target === "regulator") navigate("/regulator");
    else navigate("/consumer");
  };

  const currentView = location.pathname.startsWith("/admin")
    ? "admin"
    : location.pathname.startsWith("/brand")
    ? "brand"
    : location.pathname.startsWith("/regulator")
    ? "regulator"
    : "consumer";

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between shadow-xs">
      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="p-2 -ml-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 lg:hidden focus:outline-none focus:ring-2 focus:ring-emerald-500"
          aria-label="Open sidebar menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-black text-slate-900 tracking-tight truncate">
              {title || `Hi, ${firstName} 👋`}
            </h1>
            <span className={`hidden sm:inline-flex text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-md border ${roleStyles[userRole]}`}>
              {userRole}
            </span>
          </div>
          {subtitle && (
            <p className="text-[11px] text-slate-500 font-medium truncate hidden md:block">{subtitle}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <LanguageToggle />

        {isAdmin ? (
          <div className="flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-xl border border-slate-200">
            <span className="text-[10px] font-bold text-slate-500 hidden md:inline">View:</span>
            <select
              value={currentView}
              onChange={handleAdminViewChange}
              className="text-xs font-extrabold text-slate-800 bg-transparent border-none focus:ring-0 cursor-pointer py-0.5 pl-1 pr-6"
            >
              <option value="admin">Admin Control ⚙️</option>
              <option value="consumer">Consumer View (Preview)</option>
              <option value="brand">Brand View (Preview)</option>
              <option value="regulator">Regulator View (Preview)</option>
            </select>
          </div>
        ) : (
          <span className={`inline-flex sm:hidden text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-md border ${roleStyles[userRole]}`}>
            {userRole}
          </span>
        )}

        {userRole === "consumer" && (
          <Link
            to="/consumer/scan"
            className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold shadow-xs transition-colors"
          >
            <span>📷</span>
            <span>Scan Product</span>
          </Link>
        )}
      </div>
    </header>
  );
}
