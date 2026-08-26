import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) fetchProfile(session.user);
      else setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) fetchProfile(session.user);
      else {
        setProfile(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function fetchProfile(userOrId) {
    if (!userOrId) {
      setProfile(null);
      setLoading(false);
      return;
    }

    const userId = typeof userOrId === "string" ? userOrId : userOrId.id;
    const userObj = typeof userOrId === "object" ? userOrId : user;

    try {
      const { data, error } = await supabase
        .from("users_profile")
        .select("*")
        .eq("id", userId)
        .maybeSingle();

      if (data) {
        setProfile(data);
      } else {
        console.warn("Profile not found in DB for user:", userId, error);
        
        const metaRole = userObj?.user_metadata?.role || "consumer";
        const metaName =
          userObj?.user_metadata?.full_name ||
          userObj?.email?.split("@")[0] ||
          "User";

        const fallbackProfile = {
          id: userId,
          full_name: metaName,
          role: metaRole,
        };

        // Try to auto-create missing profile
        const { data: inserted } = await supabase
          .from("users_profile")
          .upsert(fallbackProfile)
          .select("*")
          .maybeSingle();

        setProfile(inserted || fallbackProfile);
      }
    } catch (err) {
      console.error("Error in fetchProfile:", err);
      if (userObj) {
        setProfile({
          id: userId,
          full_name: userObj?.user_metadata?.full_name || "User",
          role: userObj?.user_metadata?.role || "consumer",
        });
      }
    } finally {
      setLoading(false);
    }
  }

  async function signUp(email, password, fullName, role = "consumer") {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
          role: role,
        },
      },
    });

    if (error) throw error;

    if (data.user) {
      if (data.session) {
        await new Promise((r) => setTimeout(r, 300));
        await fetchProfile(data.user);
      }
    }

    return data;
  }

  async function signIn(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;
    await fetchProfile(data.user);
    return data;
  }

  async function signOut() {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setProfile(null);
  }

  async function switchRole(newRole) {
    if (!user) return;
    try {
      const { data, error } = await supabase
        .from("users_profile")
        .upsert({
          id: user.id,
          full_name: profile?.full_name || user.user_metadata?.full_name || user.email?.split("@")[0] || "User",
          role: newRole,
        })
        .select("*")
        .maybeSingle();

      if (data) {
        setProfile(data);
      } else {
        setProfile((prev) => ({ ...(prev || {}), id: user.id, role: newRole }));
      }
    } catch (err) {
      console.warn("Could not update role in DB, setting local state:", err);
      setProfile((prev) => ({ ...(prev || {}), id: user.id, role: newRole }));
    }
  }

  const value = {
    user,
    profile,
    loading,
    signUp,
    signIn,
    signOut,
    switchRole,
    role: profile?.role || null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
