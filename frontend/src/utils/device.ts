const DEVICE_ID_KEY = "GED_DEVICE_ID";

let inMemoryDeviceId: string | null = null;

function generateId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  // Fallback (RFC4122 v4 風ではない簡易 UUID)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function ensureDeviceId(): string {
  // SSR / テスト環境
  if (typeof window === "undefined" || !window.localStorage) {
    if (!inMemoryDeviceId) {
      inMemoryDeviceId = generateId();
    }
    return inMemoryDeviceId;
  }

  try {
    const existing = window.localStorage.getItem(DEVICE_ID_KEY);
    if (existing && existing.length > 0) {
      return existing;
    }
  } catch {
    // localStorage 読み込み失敗時は in-memory にフォールバック
    if (!inMemoryDeviceId) {
      inMemoryDeviceId = generateId();
    }
    return inMemoryDeviceId;
  }

  const id = generateId();
  try {
    window.localStorage.setItem(DEVICE_ID_KEY, id);
  } catch {
    // セットに失敗しても動作継続
  }
  return id;
}

export function getCurrentDeviceId(): string | null {
  if (typeof window === "undefined" || !window.localStorage) {
    return inMemoryDeviceId;
  }
  try {
    return window.localStorage.getItem(DEVICE_ID_KEY);
  } catch {
    return null;
  }
}
