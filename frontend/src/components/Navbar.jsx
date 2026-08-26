import { Link } from "react-router-dom";
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
  const { user, profile, role, signOut } = useAuth();
  const { t } = useTranslation();

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
            {user && profile && (
              <>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                    roleColors[role] || "bg-gray-100 text-gray-800"
                  }`}
                >
                  {role}
                </span>
                <span className="text-sm text-gray-600 hidden sm:block">
                  {profile.full_name}
                </span>
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
