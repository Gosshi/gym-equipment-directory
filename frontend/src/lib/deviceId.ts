const STORAGE_KEY = "gid:favoritesDeviceId";
const DEVICE_ID_PATTERN = /^[A-Za-z0-9_-]{8,128}$/;

let cachedDeviceId: string | null = null;

const createDeviceId = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replace(/-/g, "");
  }

  const randomPart = Math.random().toString(36).slice(2, 10);
  const timestampPart = Date.now().toString(36);
  return `gid${timestampPart}${randomPart}`;
};

export const getDeviceId = () => {
  if (cachedDeviceId) {
    return cachedDeviceId;
  }

  if (typeof window === "undefined") {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && DEVICE_ID_PATTERN.test(stored)) {
      cachedDeviceId = stored;
      return cachedDeviceId;
    }
  } catch {
    return null;
  }

  return null;
};

export const ensureDeviceId = () => {
  const existing = getDeviceId();
  if (existing) {
    return existing;
  }

  if (typeof window === "undefined") {
    return null;
  }

  const next = createDeviceId();

  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Ignore write failures (e.g. private mode), still return the generated ID.
  }

  cachedDeviceId = next;
  return next;
};

export const resetDeviceIdForTests = () => {
  if (process.env.NODE_ENV === "production") {
    return;
  }

  cachedDeviceId = null;

  if (typeof window !== "undefined") {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore storage errors in test environments.
    }
  }
};
