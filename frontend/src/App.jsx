import { Routes, Route, Navigate, Link } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Leaderboard from "./pages/Leaderboard";

// Consumer Multi-Page Experience
import ConsumerHome from "./pages/consumer/ConsumerHome";
import ScanProductPage from "./pages/consumer/ScanProductPage";
import MyScansPage from "./pages/consumer/MyScansPage";
import RulesRightsPage from "./pages/consumer/RulesRightsPage";
import PriceComparatorPage from "./pages/consumer/PriceComparatorPage";

// Brand Experience
import BrandDashboard from "./pages/BrandDashboard";
import BrandProductsPage from "./pages/brand/BrandProductsPage";
import BrandVerifyPage from "./pages/brand/BrandVerifyPage";

// Regulator Experience
import RegulatorDashboard from "./pages/RegulatorDashboard";

// Admin Experience
import AdminDashboard from "./pages/AdminDashboard";
import AdminRules from "./pages/admin/AdminRules";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminReports from "./pages/admin/AdminReports";
import AdminApiUsage from "./pages/admin/AdminApiUsage";
import AdminAuditLog from "./pages/admin/AdminAuditLog";

function NotAuthorized() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4 antialiased">
      <div className="card-slate bg-white p-8 sm:p-10 max-w-md w-full text-center space-y-4 shadow-2xl">
        <div className="w-14 h-14 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto text-2xl">
          🛡️
        </div>
        <h2 className="text-xl font-black text-slate-900 tracking-tight">Access Restricted</h2>
        <p className="text-xs text-slate-500 leading-relaxed">
          This area is restricted to authorized roles. Your current account does not have permission to access this module.
        </p>
        <div className="pt-2">
          <Link to="/dashboard" className="btn-accent w-full">
            Return to Authorized Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      {/* Public Authentication & Info */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/leaderboard"
        element={
          <Layout title="Brand Compliance Index" subtitle="Public compliance transparency leaderboard">
            <Leaderboard />
          </Layout>
        }
      />
      <Route path="/not-authorized" element={<NotAuthorized />} />

      {/* Role Gateway */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* CONSUMER MULTI-PAGE ROUTES */}
      <Route
        path="/consumer"
        element={
          <ProtectedRoute allowedRoles={["consumer", "admin"]}>
            <Layout title="Consumer Dashboard" subtitle="Packaging verification & rights portal">
              <ConsumerHome />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/consumer/scan"
        element={
          <ProtectedRoute allowedRoles={["consumer", "brand", "admin"]}>
            <Layout title="Scan Product Packaging" subtitle="AI Legal Metrology 8-field verification">
              <ScanProductPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/consumer/scans"
        element={
          <ProtectedRoute allowedRoles={["consumer", "admin"]}>
            <Layout title="My Scans History" subtitle="Audit records & compliance certificates">
              <MyScansPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/consumer/rules"
        element={
          <ProtectedRoute allowedRoles={["consumer", "brand", "regulator", "admin"]}>
            <Layout title="Legal Metrology Rules, 2011" subtitle="Mandatory declaration statutory specifications">
              <RulesRightsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/consumer/compare"
        element={
          <ProtectedRoute allowedRoles={["consumer", "admin"]}>
            <Layout title="Unit Sale Price Calculator" subtitle="Rule 6(1)(g) shrinkflation comparator">
              <PriceComparatorPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* BRAND SAAS ROUTES */}
      <Route
        path="/brand"
        element={
          <ProtectedRoute allowedRoles={["brand", "admin"]}>
            <Layout title="Brand Compliance SaaS" subtitle="Packaging pre-market QA & SKU catalog">
              <BrandDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/brand/products"
        element={
          <ProtectedRoute allowedRoles={["brand", "admin"]}>
            <Layout title="SKU Catalog & Scans" subtitle="Audited product lines & compliance certificates">
              <BrandProductsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/brand/verify"
        element={
          <ProtectedRoute allowedRoles={["brand", "admin"]}>
            <Layout title="Verify SKU Artwork" subtitle="Pre-market artwork proof verification">
              <BrandVerifyPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* REGULATOR PORTAL ROUTES */}
      <Route
        path="/regulator"
        element={
          <ProtectedRoute allowedRoles={["regulator", "admin"]}>
            <Layout title="Regulator Portal" subtitle="Compliance analytics & violation monitoring">
              <RegulatorDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/regulator/flagged"
        element={
          <ProtectedRoute allowedRoles={["regulator", "admin"]}>
            <Layout title="Flagged Violations" subtitle="Consumer grievance reports & non-compliance records">
              <RegulatorDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/regulator/scans"
        element={
          <ProtectedRoute allowedRoles={["regulator", "admin"]}>
            <Layout title="All Market Scans" subtitle="Ecosystem-wide packaging audit telemetry">
              <RegulatorDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* ADMIN CONTROL CENTER ROUTES */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="Admin Control Center" subtitle="System governance & platform monitoring">
              <AdminDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/rules"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="Rule Configurations" subtitle="Legal Metrology weights & keywords management">
              <AdminRules />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="User Management" subtitle="Platform accounts & RBAC permissions">
              <AdminUsers />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="Grievance Reports" subtitle="Consumer reports & enforcement investigations">
              <AdminReports />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/api-usage"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="API Usage Telemetry" subtitle="Endpoint request metrics & quota monitoring">
              <AdminApiUsage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/audit-log"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout title="System Audit Logs" subtitle="Security & configuration change history">
              <AdminAuditLog />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Default Catch-all */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
