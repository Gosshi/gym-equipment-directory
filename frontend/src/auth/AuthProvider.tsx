"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { LoginDialog } from "@/components/auth/LoginDialog";
import { toast } from "@/components/ui/use-toast";
import { favoritesStore } from "@/store/favoritesStore";
import { historyStore } from "@/store/historyStore";
import type { User } from "@/types/user";

import { authClient, authMode, type AuthMode, type AuthSignInParams } from "./authClient";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  mode: AuthMode;
  signIn(params: AuthSignInParams): Promise<User>;
  signOut(): Promise<void>;
  getToken(): Promise<string | null>;
  openLoginDialog(): void;
  closeLoginDialog(): void;
  requireAuth(): Promise<User>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isDialogOpen, setDialogOpen] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = useState(false);

  const pendingAuthRef = useRef<{
    resolve: (value: User) => void;
    reject: (reason?: unknown) => void;
  } | null>(null);
  const mountedRef = useRef(true);

  const syncUserData = useCallback((userId: string) => {
    const favorites = favoritesStore.getState();
    const history = historyStore.getState();

    favorites.setAuthenticated(true);
    history.setAuthenticated(true);

    favorites.syncWithServer(userId).catch((error) => {
      const message =
        error instanceof Error && error.message
          ? error.message
          : "お気に入りの同期に失敗しました。";
      toast({
        title: "お気に入りの同期に失敗しました",
        description: message,
        variant: "destructive",
      });
    });

    history.syncWithServer(userId).catch((error) => {
      const message =
        error instanceof Error && error.message
          ? error.message
          : "閲覧履歴の同期に失敗しました。";
      toast({
        title: "閲覧履歴の同期に失敗しました",
        description: message,
        variant: "destructive",
      });
    });
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    authClient
      .getSession()
      .then((session) => {
        if (cancelled) {
          return;
        }
        if (session) {
          favoritesStore.getState().setAuthenticated(true);
          historyStore.getState().setAuthenticated(true);
          setUser(session.user);
          setToken(session.token);
          setStatus("authenticated");
          syncUserData(session.user.id);
        } else {
          favoritesStore.getState().setAuthenticated(false);
          historyStore.getState().setAuthenticated(false);
          setUser(null);
          setToken(null);
          setStatus("unauthenticated");
        }
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        favoritesStore.getState().setAuthenticated(false);
        historyStore.getState().setAuthenticated(false);
        setUser(null);
        setToken(null);
        setStatus("unauthenticated");
      });

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [syncUserData]);

  const resolvePendingAuth = useCallback(
    (value: User | null, error?: unknown) => {
      const pending = pendingAuthRef.current;
      if (!pending) {
        return;
      }

      pendingAuthRef.current = null;
      if (value) {
        pending.resolve(value);
      } else {
        pending.reject(error);
      }
    },
    [],
  );

  const performSignIn = useCallback(
    async (params: AuthSignInParams) => {
      setIsSigningIn(true);
      setSignInError(null);
      try {
        const session = await authClient.signIn(params);
        if (!mountedRef.current) {
          return session.user;
        }
        setUser(session.user);
        setToken(session.token);
        setStatus("authenticated");
        setDialogOpen(false);
        resolvePendingAuth(session.user);
        syncUserData(session.user.id);
        return session.user;
      } catch (error) {
        if (mountedRef.current) {
          const message = error instanceof Error ? error.message : "サインインに失敗しました。";
          setSignInError(message);
        }
        throw error;
      } finally {
        if (mountedRef.current) {
          setIsSigningIn(false);
        }
      }
    },
    [resolvePendingAuth, syncUserData],
  );

  const signOut = useCallback(async () => {
    try {
      await authClient.signOut();
    } finally {
      if (!mountedRef.current) {
        return;
      }
      favoritesStore.getState().setAuthenticated(false);
      historyStore.getState().setAuthenticated(false);
      setUser(null);
      setToken(null);
      setStatus("unauthenticated");
      resolvePendingAuth(null, new Error("Authentication cancelled"));
    }
  }, [resolvePendingAuth]);

  const getToken = useCallback(async () => {
    if (token) {
      return token;
    }
    const fresh = await authClient.getToken();
    if (mountedRef.current) {
      setToken(fresh);
    }
    return fresh;
  }, [token]);

  const openLoginDialog = useCallback(() => {
    setSignInError(null);
    setDialogOpen(true);
  }, []);

  const closeLoginDialog = useCallback(() => {
    setDialogOpen(false);
    if (!user) {
      resolvePendingAuth(null, new Error("Authentication cancelled"));
    }
  }, [resolvePendingAuth, user]);

  const requireAuth = useCallback(async () => {
    if (user) {
      return user;
    }
    openLoginDialog();
    return new Promise<User>((resolve, reject) => {
      resolvePendingAuth(null, new Error("Authentication superseded"));
      pendingAuthRef.current = { resolve, reject };
    });
  }, [openLoginDialog, resolvePendingAuth, user]);

  const handleDialogOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) {
        openLoginDialog();
      } else {
        closeLoginDialog();
      }
    },
    [closeLoginDialog, openLoginDialog],
  );

  const contextValue = useMemo<AuthContextValue>(() => ({
    status,
    user,
    mode: authMode,
    signIn: performSignIn,
    signOut,
    getToken,
    openLoginDialog,
    closeLoginDialog,
    requireAuth,
  }), [closeLoginDialog, getToken, openLoginDialog, performSignIn, requireAuth, signOut, status, user]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      <LoginDialog
        errorMessage={signInError}
        isSubmitting={isSigningIn}
        mode={authMode}
        onOpenChange={handleDialogOpenChange}
        onSignIn={async (nickname) => {
          try {
            await performSignIn({ nickname });
          } catch {
            // エラーは performSignIn 内で状態管理済み（signInError）
          }
        }}
        open={isDialogOpen}
        status={status}
      />
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
