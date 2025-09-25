const SELECTED_PARAM = "selected";
const ALLOWED_SELECTED_PATTERN = /^[A-Za-z0-9-._~]+$/;

const sanitizeSelectedValue = (value: string | null | undefined): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (!ALLOWED_SELECTED_PATTERN.test(trimmed)) {
    return null;
  }
  return trimmed;
};

export const getSelectedFromSearchParams = (
  input: URLSearchParams | string | null | undefined,
): string | null => {
  if (!input) {
    return null;
  }
  const params = typeof input === "string" ? new URLSearchParams(input) : input;
  const value = params.get(SELECTED_PARAM);
  return sanitizeSelectedValue(value);
};

export const setSelectedOnSearchParams = (
  input: URLSearchParams | string,
  value: string | null,
): string => {
  const source = typeof input === "string" ? input : input.toString();
  const params = new URLSearchParams(source);
  const sanitized = sanitizeSelectedValue(value);

  if (value != null && sanitized === null) {
    return source;
  }

  if (sanitized) {
    params.set(SELECTED_PARAM, sanitized);
  } else {
    params.delete(SELECTED_PARAM);
  }
  return params.toString();
};

export const clearSelectedFromSearchParams = (
  input: URLSearchParams | string,
): string => {
  const params = new URLSearchParams(typeof input === "string" ? input : input.toString());
  params.delete(SELECTED_PARAM);
  return params.toString();
};

export const isSelectedMatching = (candidate: string | null | undefined, expected: string | null): boolean => {
  if (!expected) {
    return candidate == null;
  }
  return sanitizeSelectedValue(candidate) === expected;
};
