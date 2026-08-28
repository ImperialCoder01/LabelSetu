import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { supabase } from "../../lib/supabase";
import AppDrawer from "../../components/AppDrawer";

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "https://labelsetu.onrender.com").replace(/\/$/, "");

const CATEGORIES = [
  "Food & Beverages",
  "Dairy Products",
  "Personal Care & Cosmetics",
  "Home Care & Cleaning",
  "Snacks & Confectionery",
  "Spices & Condiments",
  "Edible Oils & Ghee",
  "Electronics & Appliances",
  "Pharmaceuticals & Health",
  "Packaged Commodities",
];

async function optimizeImageForUpload(file, maxDimension = 1600, quality = 0.88) {
  if (!file || !file.type || !file.type.startsWith("image/")) return file;
  return new Promise((resolve) => {
    try {
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(objectUrl);
        let { width, height } = img;
        if (width <= maxDimension && height <= maxDimension) {
          resolve(file);
          return;
        }
        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(file);
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file);
              return;
            }
            const cleanName = file.name ? file.name.replace(/\.[^/.]+$/, ".jpg") : "upload.jpg";
            const optimized = new File([blob], cleanName, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            resolve(optimized);
          },
          "image/jpeg",
          quality
        );
      };
      img.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        resolve(file);
      };
      img.src = objectUrl;
    } catch (_) {
      resolve(file);
    }
  });
}

export default function BrandProductsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("products"); // 'products' | 'register' | 'analytics' | 'bulk'
  const [products, setProducts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Wizard state
  const [wizardStep, setWizardStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [wizardSuccess, setWizardSuccess] = useState(false);
  const [wizardError, setWizardError] = useState(null);

  // Version modal
  const [versionModalOpen, setVersionModalOpen] = useState(false);
  const [versionSummary, setVersionSummary] = useState("");
  const [versionMrp, setVersionMrp] = useState("");
  const [versionNetQty, setVersionNetQty] = useState("");

  const [formData, setFormData] = useState({
    product_name: "",
    brand_name: "",
    category: "Food & Beverages",
    subcategory: "",
    sku: "",
    barcode: "",
    barcode_type: "EAN-13",
    description: "",
    mrp: "",
    net_quantity: "",
    unit_sale_price: "",
    manufacturing_date_info: "",
    expiry_info: "",
    batch_info: "",
    manufacturer_name_address: "",
    packer_name_address: "",
    importer_name_address: "",
    country_of_origin: "India",
    consumer_care: "",
    fssai_lic: "",
    ingredients: "",
    veg_non_veg: "VEGETARIAN",
    primary_image_url: "",
    front_image_url: "",
    back_image_url: "",
  });

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`${API_BASE}/api/products`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProducts(data || []);
      }

      // Fetch analytics
      const aRes = await fetch(`${API_BASE}/api/verification/analytics`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (aRes.ok) {
        const aData = await aRes.json();
        setAnalytics(aData);
      }
    } catch (err) {
      console.error("Failed to load products:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setWizardError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Authentication required");

      const payload = {
        ...formData,
        mrp: formData.mrp ? parseFloat(formData.mrp) : null,
      };

      const res = await fetch(`${API_BASE}/api/products`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to register product");
      }

      setWizardSuccess(true);
      fetchProducts();
      setTimeout(() => {
        setWizardSuccess(false);
        setActiveTab("products");
        setWizardStep(1);
      }, 2000);
    } catch (err) {
      setWizardError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateVersion = async (e) => {
    e.preventDefault();
    if (!selectedProduct) return;
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const updates = {};
      if (versionMrp) updates.mrp = parseFloat(versionMrp);
      if (versionNetQty) updates.net_quantity = versionNetQty;

      const res = await fetch(`${API_BASE}/api/products/${selectedProduct.id}/version`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          change_summary: versionSummary,
          updates: Object.keys(updates).length > 0 ? updates : null,
        }),
      });
      if (!res.ok) throw new Error("Failed to create version");
      setVersionModalOpen(false);
      setVersionSummary("");
      fetchProducts();
      alert("New product revision recorded successfully!");
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "approved":
        return <span className="badge-pass font-bold">APPROVED & VERIFIED</span>;
      case "pending_approval":
        return <span className="badge-partial font-bold">PENDING APPROVAL</span>;
      case "suspended":
        return <span className="badge-fail font-bold">SUSPENDED</span>;
      case "rejected":
        return <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold">REJECTED</span>;
      default:
        return <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs font-bold">{status?.toUpperCase() || "DRAFT"}</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Manufacturer Product Hub</h1>
          <p className="text-xs text-slate-500 mt-1">Authoritative SKU registration, packaging version control & anti-cloning telemetry</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab("products")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "products" ? "bg-slate-900 text-white shadow" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            📦 My Registered SKUs ({products.length})
          </button>
          <button
            onClick={() => setActiveTab("register")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "register" ? "bg-emerald-600 text-white shadow" : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
            }`}
          >
            ➕ Register New Product
          </button>
          <button
            onClick={() => setActiveTab("analytics")}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === "analytics" ? "bg-indigo-600 text-white shadow" : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            }`}
          >
            📊 Verification Telemetry
          </button>
        </div>
      </div>

      {/* TAB 1: PRODUCT LIST */}
      {activeTab === "products" && (
        <div className="space-y-4">
          {loading ? (
            <div className="card-slate p-8 text-center text-slate-400 font-bold">Loading registered products...</div>
          ) : products.length === 0 ? (
            <div className="card-slate p-12 text-center space-y-3">
              <div className="text-4xl">🏷️</div>
              <h3 className="text-base font-extrabold text-slate-800">No Registered Products Yet</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Register your packaged commodities to enable consumer authenticity verification, Legal Metrology compliance certificates, and anti-cloning monitoring.
              </p>
              <button
                onClick={() => setActiveTab("register")}
                className="btn-accent px-6 py-2.5 text-xs inline-block mt-2"
              >
                Register First Product
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((p) => (
                <div
                  key={p.id}
                  className="card-slate p-5 hover:border-slate-400 transition-all flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-black uppercase text-indigo-600 tracking-wider">{p.category}</span>
                        <h3 className="text-base font-black text-slate-900 leading-snug">{p.product_name}</h3>
                        <p className="text-xs font-bold text-slate-500">Brand: {p.brand_name}</p>
                      </div>
                      {getStatusBadge(p.status)}
                    </div>

                    <div className="bg-slate-50 p-3 rounded-xl space-y-1 text-xs text-slate-600 font-mono">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Barcode:</span>
                        <span className="font-bold text-slate-800">{p.barcode}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Reg. MRP:</span>
                        <span className="font-bold text-emerald-700">{p.mrp ? `₹${p.mrp}` : "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Net Qty:</span>
                        <span className="font-bold text-slate-800">{p.net_quantity || "N/A"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                    <button
                      onClick={() => {
                        setSelectedProduct(p);
                        setDrawerOpen(true);
                      }}
                      className="text-indigo-600 font-bold hover:underline"
                    >
                      View Specifications →
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProduct(p);
                        setVersionModalOpen(true);
                      }}
                      className="text-slate-600 hover:text-slate-900 font-bold"
                    >
                      + New Version
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: REGISTER NEW PRODUCT WIZARD */}
      {activeTab === "register" && (
        <div className="card-slate p-6 sm:p-8 max-w-4xl mx-auto space-y-6">
          <div className="border-b border-slate-200 pb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-900">Authoritative SKU Registration Wizard</h2>
              <p className="text-xs text-slate-500">Step {wizardStep} of 3 — Enter official commodity declarations</p>
            </div>
            <div className="flex gap-2">
              {[1, 2, 3].map((step) => (
                <div
                  key={step}
                  className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black ${
                    wizardStep === step ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {step}
                </div>
              ))}
            </div>
          </div>

          {wizardSuccess && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold">
              ✓ Product registered successfully! Submitted for Administrative approval.
            </div>
          )}

          {wizardError && (
            <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-bold">
              ⚠️ {wizardError}
            </div>
          )}

          <form onSubmit={handleRegisterSubmit} className="space-y-6">
            {/* STEP 1: IDENTITY */}
            {wizardStep === 1 && (
              <div className="space-y-4">
                <h3 className="text-xs font-black text-indigo-700 uppercase tracking-wider">1. Brand & Commodity Identity</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Product / Commodity Name *</label>
                    <input
                      type="text"
                      name="product_name"
                      required
                      value={formData.product_name}
                      onChange={handleInputChange}
                      placeholder="e.g. Tata Salt Vacuum Evaporated"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Brand Name *</label>
                    <input
                      type="text"
                      name="brand_name"
                      required
                      value={formData.brand_name}
                      onChange={handleInputChange}
                      placeholder="e.g. Tata"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Category *</label>
                    <select
                      name="category"
                      value={formData.category}
                      onChange={handleInputChange}
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Subcategory / SKU</label>
                    <input
                      type="text"
                      name="sku"
                      value={formData.sku}
                      onChange={handleInputChange}
                      placeholder="e.g. SKU-TS-1KG-01"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    disabled={!formData.product_name || !formData.brand_name}
                    className="btn-accent px-6 py-2 text-xs"
                  >
                    Next: Statutory Declarations →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: STATUTORY DECLARATIONS */}
            {wizardStep === 2 && (
              <div className="space-y-4">
                <h3 className="text-xs font-black text-indigo-700 uppercase tracking-wider">2. Legal Metrology Declarations</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Maximum Retail Price (₹) *</label>
                    <input
                      type="number"
                      step="0.01"
                      name="mrp"
                      required
                      value={formData.mrp}
                      onChange={handleInputChange}
                      placeholder="e.g. 28.00"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Net Quantity *</label>
                    <input
                      type="text"
                      name="net_quantity"
                      required
                      value={formData.net_quantity}
                      onChange={handleInputChange}
                      placeholder="e.g. 1 kg / 500 g"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Unit Sale Price (USP)</label>
                    <input
                      type="text"
                      name="unit_sale_price"
                      value={formData.unit_sale_price}
                      onChange={handleInputChange}
                      placeholder="e.g. ₹28 per kg"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Manufacturer Name & Address *</label>
                    <textarea
                      rows={2}
                      name="manufacturer_name_address"
                      required
                      value={formData.manufacturer_name_address}
                      onChange={handleInputChange}
                      placeholder="e.g. Tata Consumer Products Ltd, 1 Bishop Lefroy Rd, Kolkata 700020"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Consumer Care / Grievance Helpline *</label>
                    <textarea
                      rows={2}
                      name="consumer_care"
                      required
                      value={formData.consumer_care}
                      onChange={handleInputChange}
                      placeholder="e.g. 1800-200-0520, care@tataconsumer.com"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Country of Origin</label>
                    <input
                      type="text"
                      name="country_of_origin"
                      value={formData.country_of_origin}
                      onChange={handleInputChange}
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">FSSAI Lic. (if applicable)</label>
                    <input
                      type="text"
                      name="fssai_lic"
                      value={formData.fssai_lic}
                      onChange={handleInputChange}
                      placeholder="14-digit license"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Veg / Non-Veg</label>
                    <select
                      name="veg_non_veg"
                      value={formData.veg_non_veg}
                      onChange={handleInputChange}
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    >
                      <option value="VEGETARIAN">🟢 100% Vegetarian</option>
                      <option value="NON_VEGETARIAN">🔴 Non-Vegetarian</option>
                      <option value="">N/A (Non-Food)</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 flex justify-between">
                  <button
                    type="button"
                    onClick={() => setWizardStep(1)}
                    className="btn-secondary px-6 py-2 text-xs"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardStep(3)}
                    disabled={!formData.mrp || !formData.net_quantity || !formData.manufacturer_name_address}
                    className="btn-accent px-6 py-2 text-xs"
                  >
                    Next: Barcode & Submission →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: BARCODE & SUBMISSION */}
            {wizardStep === 3 && (
              <div className="space-y-4">
                <h3 className="text-xs font-black text-indigo-700 uppercase tracking-wider">3. Barcode & Submission</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Printed Barcode (EAN/UPC/GTIN) *</label>
                    <input
                      type="text"
                      name="barcode"
                      required
                      value={formData.barcode}
                      onChange={handleInputChange}
                      placeholder="e.g. 8901262010053"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Primary Packaging Artwork Image URL</label>
                    <input
                      type="url"
                      name="primary_image_url"
                      value={formData.primary_image_url}
                      onChange={handleInputChange}
                      placeholder="https://..."
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:border-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs text-slate-600">
                  <span className="font-bold text-slate-800">Submission Declaration:</span>
                  <p>
                    By submitting this product, you certify that the statutory declarations comply with the Legal Metrology (Packaged Commodities) Rules, 2011. The submission will enter the Administrative queue for verification.
                  </p>
                </div>

                <div className="pt-4 flex justify-between">
                  <button
                    type="button"
                    onClick={() => setWizardStep(2)}
                    className="btn-secondary px-6 py-2 text-xs"
                  >
                    ← Back
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !formData.barcode}
                    className="btn-accent px-8 py-2 text-xs bg-emerald-600 hover:bg-emerald-700"
                  >
                    {submitting ? "Submitting..." : "Submit Product for Approval ✓"}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      )}

      {/* TAB 3: VERIFICATION TELEMETRY */}
      {activeTab === "analytics" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card-slate p-5 space-y-1">
              <span className="text-xs font-bold text-slate-500">Total Consumer Scans</span>
              <p className="text-3xl font-black text-slate-900">{analytics?.total_scans || 0}</p>
            </div>
            <div className="card-slate p-5 space-y-1 border-l-4 border-emerald-500">
              <span className="text-xs font-bold text-slate-500">Verified Original Scans</span>
              <p className="text-3xl font-black text-emerald-700">{analytics?.verified || 0}</p>
            </div>
            <div className="card-slate p-5 space-y-1 border-l-4 border-amber-500">
              <span className="text-xs font-bold text-slate-500">Suspicious / Velocity Alerts</span>
              <p className="text-3xl font-black text-amber-600">{analytics?.suspicious || 0}</p>
            </div>
          </div>

          <div className="card-slate p-6 space-y-4">
            <h3 className="text-sm font-black text-slate-900">Recent Consumer Verification Activity</h3>
            {analytics?.recent_events?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                    <tr>
                      <th className="p-3">Barcode</th>
                      <th className="p-3">Verification Result</th>
                      <th className="p-3">Flag</th>
                      <th className="p-3">Source</th>
                      <th className="p-3">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {analytics.recent_events.map((ev, i) => (
                      <tr key={i} className="hover:bg-slate-50 font-mono">
                        <td className="p-3 font-bold text-slate-900">{ev.barcode}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            ev.result === "VERIFIED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                          }`}>
                            {ev.result}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            ev.suspicious_flag === "NORMAL" ? "text-slate-500" : "bg-rose-100 text-rose-700"
                          }`}>
                            {ev.suspicious_flag}
                          </span>
                        </td>
                        <td className="p-3 text-slate-500">{ev.verification_source}</td>
                        <td className="p-3 text-slate-400">{new Date(ev.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-400">No consumer scan events logged yet.</p>
            )}
          </div>
        </div>
      )}

      {/* DRAWER: PRODUCT DETAILS */}
      <AppDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={selectedProduct?.product_name || "Product Specifications"}
        subtitle={`Barcode: ${selectedProduct?.barcode || ""} | Brand: ${selectedProduct?.brand_name || ""}`}
      >
        {selectedProduct && (
          <div className="space-y-4 text-xs">
            <div className="flex justify-between items-center bg-slate-50 p-3 rounded-xl">
              <span className="font-bold text-slate-600">Approval Status:</span>
              {getStatusBadge(selectedProduct.status)}
            </div>

            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-black text-slate-800">Mandatory Declarations</h4>
              <div className="grid grid-cols-2 gap-2 text-slate-600">
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">MRP:</span>
                  <span className="font-bold text-emerald-700">₹{selectedProduct.mrp || "N/A"}</span>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Net Quantity:</span>
                  <span className="font-bold text-slate-800">{selectedProduct.net_quantity || "N/A"}</span>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Unit Sale Price:</span>
                  <span className="font-bold text-slate-800">{selectedProduct.unit_sale_price || "N/A"}</span>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <span className="text-slate-400 block text-[10px]">Country of Origin:</span>
                  <span className="font-bold text-slate-800">{selectedProduct.country_of_origin || "India"}</span>
                </div>
              </div>
            </div>

            <div className="space-y-1 border-t border-slate-100 pt-3">
              <span className="text-slate-400 text-[10px] block font-bold">Manufacturer Name & Address:</span>
              <p className="font-medium text-slate-800 bg-slate-50 p-2.5 rounded">{selectedProduct.manufacturer_name_address || "N/A"}</p>
            </div>

            <div className="space-y-1 border-t border-slate-100 pt-3">
              <span className="text-slate-400 text-[10px] block font-bold">Consumer Care Helpline:</span>
              <p className="font-medium text-slate-800 bg-slate-50 p-2.5 rounded">{selectedProduct.consumer_care || "N/A"}</p>
            </div>

            {selectedProduct.versions?.length > 0 && (
              <div className="space-y-2 border-t border-slate-100 pt-3">
                <h4 className="font-black text-slate-800">Version History ({selectedProduct.versions.length})</h4>
                <div className="space-y-2">
                  {selectedProduct.versions.map((v, idx) => (
                    <div key={idx} className="p-2.5 bg-slate-50 rounded-lg text-[11px] space-y-1">
                      <div className="flex justify-between font-bold text-slate-700">
                        <span>Revision v{v.version_number}</span>
                        <span className="text-slate-400">{new Date(v.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-500">{v.change_summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </AppDrawer>

      {/* VERSION MODAL */}
      {versionModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-base font-black text-slate-900">Record New SKU Revision</h3>
            <p className="text-xs text-slate-500">
              Create a revision snapshot for '{selectedProduct?.product_name}' to maintain historical compliance traceability.
            </p>
            <form onSubmit={handleCreateVersion} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Change Summary *</label>
                <textarea
                  rows={2}
                  required
                  value={versionSummary}
                  onChange={(e) => setVersionSummary(e.target.value)}
                  placeholder="e.g. Updated MRP to ₹30.00 and redesigned back panel artwork"
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-300 outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">New MRP (optional)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={versionMrp}
                    onChange={(e) => setVersionMrp(e.target.value)}
                    placeholder="₹..."
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">New Net Qty (optional)</label>
                  <input
                    type="text"
                    value={versionNetQty}
                    onChange={(e) => setVersionNetQty(e.target.value)}
                    placeholder="e.g. 1.2 kg"
                    className="w-full text-xs p-2 rounded-lg border border-slate-300 outline-none"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setVersionModalOpen(false)}
                  className="btn-secondary px-4 py-2 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!versionSummary}
                  className="btn-accent px-5 py-2 text-xs"
                >
                  Save Revision Snapshot ✓
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
