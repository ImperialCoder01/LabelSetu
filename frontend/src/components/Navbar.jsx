import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTranslation } from "react-i18next";
import LanguageToggle from "./LanguageToggle";
import Logo from "./Logo";

const roleColors = {
  consumer: "bg-sky-100 text-sky-900 border border-sky-300",
  brand: "bg-purple-100 text-purple-900 border border-purple-300",
  regulator: "bg-amber-100 text-amber-900 border border-amber-300",
  admin: "bg-red-100 text-red-900 border border-red-300",
};

export default function Navbar() {
  const { user, profile, role, signOut } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <nav className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-50 backdrop-blur-md bg-slate-900/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Logo variant="dark" to="/" showBadge={true} />

          <div className="flex items-center gap-4">
            <LanguageToggle />

            {user ? (
              <>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-md text-xs font-bold capitalize ${
                    roleColors[role] || "bg-slate-700 text-white"
                  }`}>
                    {role || "consumer"}
                  </span>
                </div>

                <button
                  onClick={async () => {
                    await signOut();
                    navigate("/login");
                  }}
                  className="text-xs font-medium text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-slate-800"
                >
                  {t("common.signOut")}
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="btn-secondary text-xs py-1.5">
                  Sign In
                </Link>
                <Link to="/signup" className="btn-accent text-xs py-1.5">
                  Register Free
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
