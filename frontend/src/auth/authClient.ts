import type { User } from "@/types/user";

export type AuthMode = "stub" | "oauth";

export interface AuthSession {
  user: User;
  token: string;
}

export interface AuthSignInParams {
  nickname?: string;
  provider?: string;
}

export interface AuthClient {
  readonly mode: AuthMode;
  getSession(): Promise<AuthSession | null>;
  signIn(params: AuthSignInParams): Promise<AuthSession>;
  signOut(): Promise<void>;
  getToken(): Promise<string | null>;
}

const AUTH_STORAGE_KEY = "ged.auth.session";

const resolveAuthMode = (value: string | undefined): AuthMode => {
  if (!value) {
    return "stub";
  }

  const normalized = value.trim().toLowerCase();
  return normalized === "oauth" ? "oauth" : "stub";
};

const AUTH_MODE = resolveAuthMode(process.env.NEXT_PUBLIC_AUTH_MODE);

const isBrowser = () => typeof window !== "undefined";

const readStubSession = (): AuthSession | null => {
  if (!isBrowser()) {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as AuthSession | null;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    if (!parsed.user || typeof parsed.user !== "object" || typeof parsed.token !== "string") {
      return null;
    }
    return {
      token: parsed.token,
      user: {
        id: String((parsed.user as User).id),
        name: String((parsed.user as User).name),
        avatarUrl: (parsed.user as User).avatarUrl ?? undefined,
        email: (parsed.user as User).email ?? undefined,
      },
    };
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.warn("Failed to parse stub auth session", error);
    }
    return null;
  }
};

const writeStubSession = (session: AuthSession) => {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
};

const clearStubSession = () => {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
};

const createAvatarUrl = (name: string) => {
  const seed = encodeURIComponent(name.trim() || "guest");
  return `https://api.dicebear.com/7.x/initials/svg?seed=${seed}`;
};

const createStubClient = (): AuthClient => ({
  mode: "stub",
  async getSession() {
    return readStubSession();
  },
  async signIn(params: AuthSignInParams) {
    const nickname = params.nickname?.trim();
    if (!nickname) {
      throw new Error("ニックネームを入力してください。");
    }

    const token = `stub.${typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`;
    const user: User = {
      id:
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : Date.now().toString(36),
      name: nickname,
      avatarUrl: createAvatarUrl(nickname),
    };

    const session: AuthSession = { token, user };
    writeStubSession(session);
    return session;
  },
  async signOut() {
    clearStubSession();
  },
  async getToken() {
    const session = readStubSession();
    return session?.token ?? null;
  },
});

const createOAuthClient = (): AuthClient => ({
  mode: "oauth",
  async getSession() {
    // TODO: Implement session retrieval by calling the backend (e.g. GET /auth/session).
    return null;
  },
  async signIn(params: AuthSignInParams) {
    void params;
    // TODO: Implement OAuth login initiation sequence.
    // Expected flow: call POST /auth/login to get redirect URL, navigate to provider,
    // handle /auth/callback, then finalize by fetching /auth/session to hydrate user state.
    throw new Error("OAuth sign-in is not implemented yet.");
  },
  async signOut() {
    // TODO: Implement OAuth sign-out by revoking the session on the backend.
    throw new Error("OAuth sign-out is not implemented yet.");
  },
  async getToken() {
    // TODO: Retrieve session token from secure storage once OAuth is available.
    return null;
  },
});

export const createAuthClient = (mode: AuthMode = AUTH_MODE): AuthClient => {
  if (mode === "oauth") {
    return createOAuthClient();
  }
  return createStubClient();
};

export const authClient = createAuthClient();
export const authMode = authClient.mode;
