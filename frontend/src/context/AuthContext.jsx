import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user);
      } else {
        setProfile(null);
        setLoading(false);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user);
      } else {
        setUser(null);
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

      if (data && data.role) {
        setProfile(data);
      } else {
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

        const { data: inserted } = await supabase
          .from("users_profile")
          .upsert(fallbackProfile)
          .select("*")
          .maybeSingle();

        setProfile(inserted || fallbackProfile);
      }
    } catch (err) {
      console.error("Error fetching user profile:", err);
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
      try {
        await supabase.from("users_profile").upsert({
          id: data.user.id,
          full_name: fullName,
          role: role,
        });
      } catch (_) {}

      if (data.session) {
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
    if (data.user) {
      await fetchProfile(data.user);
    }
    return data;
  }

  async function signOut() {
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn("SignOut exception:", err);
    } finally {
      setUser(null);
      setProfile(null);
      setLoading(false);
    }
  }

  const effectiveRole = profile?.role || user?.user_metadata?.role || "consumer";

  const value = {
    user,
    profile,
    loading,
    signUp,
    signIn,
    signOut,
    role: effectiveRole,
    isAdmin: effectiveRole === "admin",
    isConsumer: effectiveRole === "consumer",
    isBrand: effectiveRole === "brand",
    isRegulator: effectiveRole === "regulator",
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
