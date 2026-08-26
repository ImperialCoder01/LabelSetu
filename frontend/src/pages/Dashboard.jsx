import { useAuth } from "../context/AuthContext";
import ConsumerDashboard from "./ConsumerDashboard";
import BrandDashboard from "./BrandDashboard";
import RegulatorDashboard from "./RegulatorDashboard";
import AdminDashboard from "./AdminDashboard";

export default function Dashboard() {
  const { role, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  switch (role) {
    case "consumer":
      return <ConsumerDashboard />;
    case "brand":
      return <BrandDashboard />;
    case "regulator":
      return <RegulatorDashboard />;
    case "admin":
      return <AdminDashboard />;
    default:
      return (
        <div className="text-center py-20">
          <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-500 mt-2">
            Role not recognized. Please contact support.
          </p>
        </div>
      );
  }
}
