import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";

const roleColors = {
  consumer: "bg-blue-100 text-blue-800",
  brand: "bg-purple-100 text-purple-800",
  regulator: "bg-amber-100 text-amber-800",
  admin: "bg-red-100 text-red-800",
};

const statusConfig = {
  active: { bg: "bg-green-100 text-green-800", label: "Active" },
  suspended: { bg: "bg-red-100 text-red-800", label: "Suspended" },
  pending_approval: { bg: "bg-amber-100 text-amber-800", label: "Pending" },
};

const allRoles = ["consumer", "brand", "regulator", "admin"];
const allStatuses = ["active", "suspended", "pending_approval"];

function Modal({ open, onClose, title, description, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="fixed inset-0 bg-black/40" />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {description && <p className="text-sm text-gray-500">{description}</p>}
        {children}
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const { profile } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [approveModal, setApproveModal] = useState(null);
  const [suspendModal, setSuspendModal] = useState(null);
  const [roleModal, setRoleModal] = useState(null);
  const [newRole, setNewRole] = useState("");
  const [acting, setActing] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => { fetchUsers(); }, []);

  async function fetchUsers() {
    const { data, error } = await supabase.from("users_profile").select("*").order("created_at", { ascending: false });
    if (!error) setUsers(data);
    setLoading(false);
  }

  function showToast(type, message) {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4000);
  }

  async function logAudit(targetId, oldVal, newVal) {
    await supabase.from("audit_log").insert({
      admin_id: profile.id,
      action_type: "UPDATE",
      target_table: "users_profile",
      target_id: targetId,
      old_value: oldVal,
      new_value: newVal,
    });
  }

  async function handleApproveBrand() {
    if (!approveModal) return;
    setActing(true);
    const user = approveModal;
    const { error } = await supabase.from("users_profile").update({ status: "active" }).eq("id", user.id);
    if (error) {
      showToast("error", "Failed to approve brand: " + error.message);
    } else {
      await logAudit(user.id, { status: user.status }, { status: "active" });
      showToast("success", `${user.full_name || "Brand"} approved successfully`);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, status: "active" } : u)));
    }
    setApproveModal(null);
    setActing(false);
  }

  async function handleSuspend() {
    if (!suspendModal) return;
    setActing(true);
    const user = suspendModal;
    const newStatus = user.status === "suspended" ? "active" : "suspended";
    const { error } = await supabase.from("users_profile").update({ status: newStatus }).eq("id", user.id);
    if (error) {
      showToast("error", "Failed to update status: " + error.message);
    } else {
      await logAudit(user.id, { status: user.status }, { status: newStatus });
      showToast("success", `${user.full_name || "User"} ${newStatus === "suspended" ? "suspended" : "reactivated"}`);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, status: newStatus } : u)));
    }
    setSuspendModal(null);
    setActing(false);
  }

  async function handleChangeRole() {
    if (!roleModal || !newRole || newRole === roleModal.role) { setRoleModal(null); return; }
    setActing(true);
    const user = roleModal;
    const { error } = await supabase.from("users_profile").update({ role: newRole }).eq("id", user.id);
    if (error) {
      showToast("error", "Failed to change role: " + error.message);
    } else {
      await logAudit(user.id, { role: user.role }, { role: newRole });
      showToast("success", `${user.full_name || "User"} role changed to ${newRole}`);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, role: newRole } : u)));
    }
    setRoleModal(null);
    setActing(false);
  }

  const filtered = users.filter((u) => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false;
    if (statusFilter !== "all" && u.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (u.full_name || "").toLowerCase().includes(q) || u.id.toLowerCase().includes(q);
    }
    return true;
  });

  const roleCounts = users.reduce((acc, u) => { acc[u.role] = (acc[u.role] || 0) + 1; return acc; }, {});
  const statusCounts = users.reduce((acc, u) => { acc[u.status || "active"] = (acc[u.status || "active"] || 0) + 1; return acc; }, {});

  return (
    <div className="space-y-6">
      {toast && (
        <div className={`fixed top-4 right-4 z-[100] px-4 py-3 rounded-lg text-sm font-medium shadow-lg transition-all ${toast.type === "success" ? "bg-green-600 text-white" : "bg-red-600 text-white"}`}>
          {toast.message}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <p className="text-gray-500 mt-1">{users.length} registered users &middot; {statusCounts.pending_approval || 0} pending approval</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {allRoles.map((r) => (
          <button key={r} onClick={() => setRoleFilter(roleFilter === r ? "all" : r)} className={`p-3 rounded-lg border-2 transition-colors text-left ${roleFilter === r ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
            <p className="text-2xl font-bold capitalize text-gray-900">{roleCounts[r] || 0}</p>
            <p className="text-xs text-gray-500 capitalize">{r}s</p>
          </button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {allStatuses.map((s) => (
          <button key={s} onClick={() => setStatusFilter(statusFilter === s ? "all" : s)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${statusFilter === s ? "ring-2 ring-primary-500 " + statusConfig[s].bg : statusConfig[s].bg + " opacity-60 hover:opacity-100"}`}>
            {statusConfig[s].label} ({statusCounts[s] || 0})
          </button>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <input type="text" placeholder="Search by name, email, or ID..." value={search} onChange={(e) => setSearch(e.target.value)} className="input-field text-sm flex-1" />
          <span className="text-xs text-gray-400 whitespace-nowrap">{filtered.length} users</span>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (<div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No users match your filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-3 px-3 font-medium text-gray-500">Name</th>
                  <th className="py-3 px-3 font-medium text-gray-500">User ID</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Role</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Status</th>
                  <th className="py-3 px-3 font-medium text-gray-500">Joined</th>
                  <th className="py-3 px-3 font-medium text-gray-500 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => {
                  const status = statusConfig[u.status || "active"];
                  return (
                    <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-3 px-3 font-medium text-gray-900">{u.full_name || "\u2014"}</td>
                      <td className="py-3 px-3 text-gray-500 font-mono text-xs">{u.id.substring(0, 12)}...</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${roleColors[u.role] || "bg-gray-100 text-gray-700"}`}>{u.role}</span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${status.bg}`}>{status.label}</span>
                      </td>
                      <td className="py-3 px-3 text-gray-500 text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "\u2014"}</td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {u.role === "brand" && u.status === "pending_approval" && (
                            <button onClick={() => setApproveModal(u)} className="px-2.5 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors border border-green-200">Approve</button>
                          )}
                          {u.role !== "admin" && (
                            <button onClick={() => setSuspendModal(u)} className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors border ${u.status === "suspended" ? "text-green-700 bg-green-50 hover:bg-green-100 border-green-200" : "text-red-700 bg-red-50 hover:bg-red-100 border-red-200"}`}>
                              {u.status === "suspended" ? "Reactivate" : "Suspend"}
                            </button>
                          )}
                          <button onClick={() => { setRoleModal(u); setNewRole(u.role); }} className="px-2.5 py-1 text-xs font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors border border-primary-200">Role</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={!!approveModal} onClose={() => setApproveModal(null)} title="Approve Brand" description={`Approve "${approveModal?.full_name || "this brand"}" and grant them active status?`}>
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={() => setApproveModal(null)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleApproveBrand} disabled={acting} className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2">
            {acting && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            Approve Brand
          </button>
        </div>
      </Modal>

      <Modal open={!!suspendModal} onClose={() => setSuspendModal(null)} title={suspendModal?.status === "suspended" ? "Reactivate User" : "Suspend User"} description={suspendModal?.status === "suspended" ? `Reactivate "${suspendModal?.full_name || "this user"}"? They will regain access.` : `Suspend "${suspendModal?.full_name || "this user"}"? They will lose access until reactivated.`}>
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={() => setSuspendModal(null)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleSuspend} disabled={acting} className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 ${suspendModal?.status === "suspended" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}`}>
            {acting && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {suspendModal?.status === "suspended" ? "Reactivate" : "Suspend"}
          </button>
        </div>
      </Modal>

      <Modal open={!!roleModal} onClose={() => setRoleModal(null)} title="Change Role" description={`Change the role of "${roleModal?.full_name || "this user"}".`}>
        <div className="space-y-3">
          <p className="text-xs text-gray-400">Current role: <span className="font-medium text-gray-600 capitalize">{roleModal?.role}</span></p>
          <div className="grid grid-cols-2 gap-2">
            {allRoles.map((r) => (
              <button key={r} onClick={() => setNewRole(r)} className={`px-3 py-2 rounded-lg text-sm font-medium capitalize transition-all border-2 ${newRole === r ? "border-primary-500 bg-primary-50 text-primary-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}>{r}</button>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-4">
          <button onClick={() => setRoleModal(null)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">Cancel</button>
          <button onClick={handleChangeRole} disabled={acting || newRole === roleModal?.role} className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2">
            {acting && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            Save Role
          </button>
        </div>
      </Modal>
    </div>
  );
}
