import { useAuth } from "../context/AuthContext";
import LanguageToggle from "./LanguageToggle";
import { Link, useNavigate } from "react-router-dom";

export default function AppHeader({ onToggleMobileMenu, title, subtitle, breadcrumbs = [] }) {
  const { profile, role, switchRole } = useAuth();
  const navigate = useNavigate();

  const userRole = role || "consumer";

  // Derive first name dynamically
  const firstName = profile?.full_name
    ? profile.full_name.trim().split(" ")[0]
    : "User";

  const handleRoleChange = async (e) => {
    const newRole = e.target.value;
    await switchRole(newRole);
    if (newRole === "admin") navigate("/admin");
    else if (newRole === "brand") navigate("/brand");
    else if (newRole === "regulator") navigate("/regulator");
    else navigate("/consumer");
  };

  const roleStyles = {
    consumer: "bg-sky-50 text-sky-800 border-sky-200",
    brand: "bg-purple-50 text-purple-800 border-purple-200",
    regulator: "bg-amber-50 text-amber-800 border-amber-200",
    admin: "bg-red-50 text-red-800 border-red-200",
  };

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between shadow-xs">
      {/* Left Area: Hamburger + Title / Greeting */}
      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="p-2 -ml-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 lg:hidden focus:outline-none focus:ring-2 focus:ring-accent-500"
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

      {/* Right Area: Tools, Role Switcher, Language Toggle */}
      <div className="flex items-center gap-2 sm:gap-3">
        <LanguageToggle />

        {/* Role Mode Explorer */}
        <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-xl border border-slate-200/80">
          <span className="text-[11px] font-bold text-slate-500 hidden md:inline">Mode:</span>
          <select
            value={userRole}
            onChange={handleRoleChange}
            className="text-xs font-bold text-slate-800 bg-transparent border-none focus:ring-0 cursor-pointer py-0.5 pl-1 pr-6"
          >
            <option value="consumer">Consumer Audit</option>
            <option value="brand">Brand SaaS</option>
            <option value="regulator">Regulator Portal</option>
            <option value="admin">Admin Control ⚙️</option>
          </select>
        </div>

        {/* Quick CTA button on Consumer mode */}
        {userRole === "consumer" && (
          <Link
            to="/consumer/scan"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-xs font-bold shadow-xs transition-colors"
          >
            <span>📷</span>
            <span>Scan Product</span>
          </Link>
        )}
      </div>
    </header>
  );
}
