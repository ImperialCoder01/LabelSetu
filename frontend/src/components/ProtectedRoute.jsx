import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, profile, loading, role } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white p-6 rounded-lg shadow-md max-w-sm text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Profile Error</h3>
          <p className="text-sm text-gray-600 mb-4">
            Could not load profile. Please sign out and sign in again.
          </p>
          <button
            onClick={() => useAuth().signOut()}
            className="w-full bg-primary-600 text-white py-2 px-4 rounded hover:bg-primary-700 transition"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/not-authorized" replace />;
  }

  return children;
}
