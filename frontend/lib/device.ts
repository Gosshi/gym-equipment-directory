export function getOrCreateDeviceId(key = "device_id"): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(key);
  if (existing && /^[A-Za-z0-9_-]{8,128}$/.test(existing)) return existing;
  const rand = () => Math.random().toString(36).slice(2);
  const id = `${Date.now().toString(36)}_${rand()}_${rand()}`.slice(0, 48).replace(/[^A-Za-z0-9_-]/g, "");
  window.localStorage.setItem(key, id);
  return id;
}

export function readDeviceId(key = "device_id"): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}
