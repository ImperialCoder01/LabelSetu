import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { role, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-10 w-10 border-3 border-slate-300 border-t-emerald-600"></div>
      </div>
    );
  }

  if (role === "admin") return <Navigate to="/admin" replace />;
  if (role === "brand") return <Navigate to="/brand" replace />;
  if (role === "regulator") return <Navigate to="/regulator" replace />;
  return <Navigate to="/consumer" replace />;
}
