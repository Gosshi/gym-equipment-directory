import { createAuthClient } from "../authClient";

describe("stub auth client", () => {
  const STORAGE_KEY = "ged.auth.session";

  beforeEach(() => {
    window.localStorage.clear();
  });

  it("creates, reads, and clears a stub session", async () => {
    const client = createAuthClient("stub");

    expect(await client.getSession()).toBeNull();
    expect(await client.getToken()).toBeNull();

    const session = await client.signIn({ nickname: "Tester" });
    expect(session.user.name).toBe("Tester");
    expect(session.token).toMatch(/^stub\./);

    const storedRaw = window.localStorage.getItem(STORAGE_KEY);
    expect(storedRaw).not.toBeNull();

    const stored = JSON.parse(String(storedRaw));
    expect(stored.token).toBe(session.token);
    expect(stored.user.name).toBe("Tester");

    expect(await client.getToken()).toBe(session.token);

    await client.signOut();

    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(await client.getSession()).toBeNull();
  });
});
