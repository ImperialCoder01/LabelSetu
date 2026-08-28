import { useState, useEffect, useMemo, useCallback } from "react";
import { supabase } from "../lib/supabase";
import { useAuth } from "../context/AuthContext";
import AppDrawer from "../components/AppDrawer";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

export default function AdminDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("approvals"); // 'approvals' | 'cases' | 'products' | 'audit' | 'telemetry'
  const [pendingProducts, setPendingProducts] = useState([]);
  const [allProducts, setAllProducts] = useState([]);
  const [executiveReports, setExecutiveReports] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);

  // Selected item drawer
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseTimeline, setCaseTimeline] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerType, setDrawerType] = useState("product"); // 'product' | 'case'

  // Action state
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [adminComment, setAdminComment] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const headers = { Authorization: `Bearer ${session.access_token}` };

      // 1. Fetch All Products
      const prodRes = await fetch(`${API_BASE}/api/products`, { headers });
      if (prodRes.ok) {
        const pData = await prodRes.json();
        setAllProducts(pData || []);
        setPendingProducts((pData || []).filter((p) => p.status === "pending_approval"));
      }

      // 2. Fetch Executive Reports
      const caseRes = await fetch(`${API_BASE}/api/executive-reports`, { headers });
      if (caseRes.ok) {
        const cData = await caseRes.json();
        setExecutiveReports(cData || []);
      }

      // 3. Fetch Audit Logs
      const auditRes = await supabase.from("audit_log").select("*").order("timestamp", { ascending: false }).limit(50);
      if (!auditRes.error) setAuditLogs(auditRes.data || []);

      // 4. Fetch Telemetry
      const teleRes = await fetch(`${API_BASE}/api/verification/analytics`, { headers });
      if (teleRes.ok) {
        const tData = await teleRes.json();
        setTelemetry(tData);
      }
    } catch (err) {
      console.error("Failed to load admin data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleProductAction = async (productId, action, reason = "") => {
    setActionLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_BASE}/api/products/${productId}/action`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ action, reason }),
      });
      if (!res.ok) throw new Error("Action failed");
      setDrawerOpen(false);
      setRejectReason("");
      fetchData();
    } catch (err) {
      alert("Error executing action: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCaseDecision = async (caseId, decision, comments = "") => {
    setActionLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_BASE}/api/executive-reports/${caseId}/decision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ decision, comments }),
      });
      if (!res.ok) throw new Error("Decision recording failed");
      setDrawerOpen(false);
      setAdminComment("");
      fetchData();
    } catch (err) {
      alert("Error recording decision: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Administrative Governance Hub</h1>
          <p className="text-xs text-slate-500 mt-1">Authoritative product approval, enforcement case decisions & immutable audit trail</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab("approvals")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "approvals" ? "bg-amber-600 text-white shadow" : "bg-amber-50 text-amber-800 hover:bg-amber-100"
            }`}
          >
            ⏳ Product Approvals ({pendingProducts.length})
          </button>
          <button
            onClick={() => setActiveTab("cases")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "cases" ? "bg-indigo-600 text-white shadow" : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            }`}
          >
            ⚖️ Executive Cases ({executiveReports.length})
          </button>
          <button
            onClick={() => setActiveTab("products")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "products" ? "bg-slate-900 text-white shadow" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            📦 Master Registry ({allProducts.length})
          </button>
          <button
            onClick={() => setActiveTab("telemetry")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "telemetry" ? "bg-emerald-600 text-white shadow" : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
            }`}
          >
            📡 Anti-Cloning Telemetry
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "audit" ? "bg-slate-700 text-white shadow" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            📜 Audit Trail ({auditLogs.length})
          </button>
        </div>
      </div>

      {/* TAB 1: PRODUCT APPROVAL QUEUE */}
      {activeTab === "approvals" && (
        <div className="space-y-4">
          {pendingProducts.length === 0 ? (
            <div className="card-slate p-12 text-center space-y-2">
              <div className="text-4xl">✓</div>
              <h3 className="text-base font-extrabold text-slate-800">All Products Reviewed</h3>
              <p className="text-xs text-slate-500">No manufacturer product registrations are currently awaiting administrative approval.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingProducts.map((p) => (
                <div key={p.id} className="card-slate p-5 space-y-4 flex flex-col justify-between border-2 border-amber-200 bg-amber-50/10">
                  <div className="space-y-2">
                    <div className="flex justify-between items-start">
                      <span className="text-[10px] font-black uppercase text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                        Awaiting Verification
                      </span>
                      <span className="text-xs font-mono font-bold text-slate-500">{p.barcode}</span>
                    </div>
                    <h3 className="text-base font-black text-slate-900">{p.product_name}</h3>
                    <p className="text-xs text-slate-600 font-bold">Brand: {p.brand_name}</p>

                    <div className="bg-white p-3 rounded-xl space-y-1 text-xs border border-amber-100 font-mono">
                      <div className="flex justify-between">
                        <span className="text-slate-400">MRP:</span>
                        <span className="font-bold text-emerald-700">₹{p.mrp || "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Net Qty:</span>
                        <span className="font-bold text-slate-800">{p.net_quantity || "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Manufacturer:</span>
                        <span className="font-bold text-slate-800 truncate max-w-[140px]">{p.manufacturer_name_address || "N/A"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2 border-t border-slate-100 text-xs">
                    <button
                      onClick={() => {
                        setSelectedProduct(p);
                        setDrawerType("product");
                        setDrawerOpen(true);
                      }}
                      className="btn-secondary flex-1 py-1.5 text-xs font-bold"
                    >
                      Inspect Specs
                    </button>
                    <button
                      onClick={() => handleProductAction(p.id, "APPROVE")}
                      disabled={actionLoading}
                      className="btn-accent flex-1 py-1.5 text-xs font-black bg-emerald-600 hover:bg-emerald-700"
                    >
                      ✓ Approve
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EXECUTIVE CASES QUEUE */}
      {activeTab === "cases" && (
        <div className="space-y-4">
          {executiveReports.length === 0 ? (
            <div className="card-slate p-12 text-center text-slate-500 font-bold">No executive investigation cases filed.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {executiveReports.map((c) => (
                <div key={c.id} className="card-slate p-5 space-y-3 border hover:border-slate-400 transition-all flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-xs font-black text-indigo-700">{c.case_number}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                        c.severity === "CRITICAL" ? "bg-rose-100 text-rose-800" : c.severity === "HIGH" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
                      }`}>
                        {c.severity}
                      </span>
                    </div>
                    <h3 className="text-sm font-black text-slate-900">{c.description}</h3>
                    <div className="p-3 bg-slate-50 rounded-xl space-y-1 text-xs font-mono">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Barcode:</span>
                        <span className="font-bold text-slate-900">{c.barcode || "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Executive Recommendation:</span>
                        <span className="font-bold text-indigo-800">{c.recommended_action}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Status:</span>
                        <span className={`font-bold ${c.status === "APPROVED" ? "text-emerald-700" : "text-amber-700"}`}>{c.status}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2 border-t border-slate-100">
                    <button
                      onClick={async () => {
                        setSelectedCase(c);
                        setDrawerType("case");
                        setDrawerOpen(true);
                        setCaseTimeline([]);
                        try {
                          const { data: { session } } = await supabase.auth.getSession();
                          const tlRes = await fetch(`${API_BASE}/api/executive-reports/${c.id}/timeline`, {
                            headers: { Authorization: `Bearer ${session.access_token}` },
                          });
                          if (tlRes.ok) {
                            const tlData = await tlRes.json();
                            setCaseTimeline(tlData.timeline || []);
                          }
                        } catch (err) {
                          console.debug("Timeline fetch fallback:", err);
                        }
                      }}
                      className="btn-secondary flex-1 py-1.5 text-xs font-bold"
                    >
                      Review Case Evidence
                    </button>
                    {c.status === "SUBMITTED" && (
                      <button
                        onClick={() => handleCaseDecision(c.id, "APPROVED", "Approved recommendation based on evidence.")}
                        disabled={actionLoading}
                        className="btn-accent px-4 py-1.5 text-xs font-black bg-indigo-600 hover:bg-indigo-700"
                      >
                        Approve Action
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: MASTER PRODUCT REGISTRY */}
      {activeTab === "products" && (
        <div className="card-slate p-6 space-y-4">
          <h3 className="text-sm font-black text-slate-900">Ecosystem Master Product Registry</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Product Name</th>
                  <th className="p-3">Brand</th>
                  <th className="p-3">Barcode</th>
                  <th className="p-3">MRP</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {allProducts.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="p-3 font-bold text-slate-900">{p.product_name}</td>
                    <td className="p-3 font-semibold text-slate-700">{p.brand_name}</td>
                    <td className="p-3 font-mono text-slate-600">{p.barcode}</td>
                    <td className="p-3 font-mono font-bold text-emerald-700">{p.mrp ? `₹${p.mrp}` : "N/A"}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        p.status === "approved" ? "bg-emerald-100 text-emerald-800" : p.status === "suspended" ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 flex gap-2">
                      {p.status !== "suspended" ? (
                        <button
                          onClick={() => handleProductAction(p.id, "SUSPEND", "Administrative suspension for compliance investigation.")}
                          className="text-rose-600 font-bold hover:underline"
                        >
                          Suspend
                        </button>
                      ) : (
                        <button
                          onClick={() => handleProductAction(p.id, "REACTIVATE")}
                          className="text-emerald-600 font-bold hover:underline"
                        >
                          Reactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: ANTI-CLONING TELEMETRY */}
      {activeTab === "telemetry" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card-slate p-5 space-y-1">
              <span className="text-xs font-bold text-slate-500">Total Scans Evaluated</span>
              <p className="text-3xl font-black text-slate-900">{telemetry?.total_scans || 0}</p>
            </div>
            <div className="card-slate p-5 space-y-1 border-l-4 border-emerald-500">
              <span className="text-xs font-bold text-slate-500">Verified Consumer Scans</span>
              <p className="text-3xl font-black text-emerald-700">{telemetry?.verified || 0}</p>
            </div>
            <div className="card-slate p-5 space-y-1 border-l-4 border-rose-500">
              <span className="text-xs font-bold text-slate-500">Suspicious Anti-Clone Flags</span>
              <p className="text-3xl font-black text-rose-700">{telemetry?.suspicious || 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: AUDIT TRAIL */}
      {activeTab === "audit" && (
        <div className="card-slate p-6 space-y-4">
          <h3 className="text-sm font-black text-slate-900">Immutable System Audit Trail</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Action Type</th>
                  <th className="p-3">Target Entity</th>
                  <th className="p-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="p-3 font-bold text-indigo-700">{log.action_type}</td>
                    <td className="p-3 text-slate-600">{log.target_table} ({log.target_id || "N/A"})</td>
                    <td className="p-3 text-slate-400">{new Date(log.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SPECIFICATION DRAWER */}
      <AppDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={drawerType === "product" ? selectedProduct?.product_name || "Product Specs" : selectedCase?.case_number || "Case Evidence"}
        subtitle={drawerType === "product" ? `Barcode: ${selectedProduct?.barcode || ""}` : selectedCase?.report_type}
      >
        {drawerType === "product" && selectedProduct && (
          <div className="space-y-4 text-xs">
            <div className="bg-slate-50 p-3 rounded-xl space-y-1">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Brand:</span>
              <p className="font-bold text-slate-900">{selectedProduct.brand_name}</p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-50 p-2.5 rounded">
                <span className="text-slate-400 block text-[10px]">MRP:</span>
                <span className="font-bold text-emerald-700">₹{selectedProduct.mrp || "N/A"}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded">
                <span className="text-slate-400 block text-[10px]">Net Quantity:</span>
                <span className="font-bold text-slate-800">{selectedProduct.net_quantity || "N/A"}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-400 text-[10px] block font-bold">Manufacturer Address:</span>
              <p className="p-2.5 bg-slate-50 rounded text-slate-800">{selectedProduct.manufacturer_name_address || "N/A"}</p>
            </div>

            <div className="space-y-1">
              <span className="text-slate-400 text-[10px] block font-bold">Consumer Care Helpline:</span>
              <p className="p-2.5 bg-slate-50 rounded text-slate-800">{selectedProduct.consumer_care || "N/A"}</p>
            </div>

            {selectedProduct.status === "pending_approval" && (
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <button
                  onClick={() => handleProductAction(selectedProduct.id, "APPROVE")}
                  disabled={actionLoading}
                  className="btn-accent w-full py-2 text-xs bg-emerald-600 hover:bg-emerald-700"
                >
                  ✓ Approve Product Registration
                </button>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Rejection reason if applicable..."
                    className="w-full text-xs p-2 rounded border border-slate-300 outline-none"
                  />
                  <button
                    onClick={() => handleProductAction(selectedProduct.id, "REJECT", rejectReason)}
                    disabled={actionLoading || !rejectReason}
                    className="w-full py-2 rounded-lg text-xs font-bold bg-rose-100 text-rose-700 hover:bg-rose-200"
                  >
                    Reject Registration
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {drawerType === "case" && selectedCase && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl space-y-1">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Description:</span>
              <p className="text-slate-800 font-medium">{selectedCase.description}</p>
            </div>

            <div className="p-3 bg-indigo-50 rounded-xl space-y-1 text-indigo-950">
              <span className="text-indigo-500 block text-[10px] uppercase font-bold">Recommended Action:</span>
              <p className="font-extrabold text-sm">{selectedCase.recommended_action}</p>
            </div>

            {/* Reconstructed Case Timeline */}
            {caseTimeline.length > 0 && (
              <div className="space-y-2 border-t border-slate-100 pt-3">
                <h4 className="font-black text-slate-800 uppercase tracking-wider text-[10px]">Case Progression Timeline</h4>
                <div className="space-y-2 relative border-l-2 border-slate-200 ml-2 pl-3">
                  {caseTimeline.map((item, idx) => (
                    <div key={idx} className="space-y-0.5 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-indigo-600 -ml-[17px]"></span>
                        <strong className="text-slate-800">{item.title}</strong>
                      </div>
                      <p className="text-slate-500 text-[10px]">{item.details}</p>
                      <span className="text-slate-400 text-[9px] block">{new Date(item.timestamp).toLocaleString()} • {item.actor}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2 pt-3 border-t border-slate-100">
              <label className="block text-[10px] uppercase font-bold text-slate-500">Admin Decision Comments</label>
              <textarea
                rows={2}
                value={adminComment}
                onChange={(e) => setAdminComment(e.target.value)}
                placeholder="Enter comments or directions..."
                className="w-full text-xs p-2 rounded border border-slate-300 outline-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleCaseDecision(selectedCase.id, "APPROVED", adminComment)}
                  disabled={actionLoading}
                  className="btn-accent flex-1 py-2 text-xs bg-emerald-600 hover:bg-emerald-700"
                >
                  ✓ Approve Action
                </button>
                <button
                  onClick={() => handleCaseDecision(selectedCase.id, "REJECTED", adminComment)}
                  disabled={actionLoading}
                  className="flex-1 py-2 rounded-lg text-xs font-bold bg-rose-100 text-rose-700 hover:bg-rose-200"
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        )}
      </AppDrawer>
    </div>
  );
}
