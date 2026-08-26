import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTranslation } from "react-i18next";
import LanguageToggle from "./LanguageToggle";

const roleColors = {
  consumer: "bg-blue-100 text-blue-800",
  brand: "bg-purple-100 text-purple-800",
  regulator: "bg-amber-100 text-amber-800",
  admin: "bg-red-100 text-red-800",
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
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">L</span>
            </div>
            <span className="text-xl font-bold text-gray-900">LabelSetu</span>
          </Link>

          <div className="flex items-center gap-4">
            <LanguageToggle />
            {user && (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-400 font-medium hidden md:inline">Role:</span>
                  <select
                    value={role || "consumer"}
                    onChange={handleRoleChange}
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize border-none cursor-pointer focus:ring-2 focus:ring-primary-500 ${
                      roleColors[role] || "bg-gray-100 text-gray-800"
                    }`}
                  >
                    <option value="consumer">Consumer</option>
                    <option value="brand">Brand SaaS</option>
                    <option value="regulator">Regulator</option>
                    <option value="admin">Admin Panel ⚙️</option>
                  </select>
                </div>
                {profile?.full_name && (
                  <span className="text-sm text-gray-600 hidden sm:block font-medium">
                    {profile.full_name}
                  </span>
                )}
                <button
                  onClick={signOut}
                  className="text-sm text-gray-500 hover:text-red-600 transition-colors"
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
