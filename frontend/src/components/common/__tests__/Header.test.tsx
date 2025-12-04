import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider } from "@/auth/AuthProvider";

import { AppHeader } from "../Header";

describe("AppHeader", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows login button and renders user name after sign in", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <AppHeader />
      </AuthProvider>,
    );

    const loginButton = await screen.findByRole("button", { name: /login/i });
    expect(loginButton).toBeInTheDocument();

    await user.click(loginButton);

    const nicknameInput = await screen.findByLabelText("ニックネーム");
    await user.type(nicknameInput, "Alice");

    const signInButton = await screen.findByRole("button", { name: "サインイン" });
    await user.click(signInButton);

    await waitFor(() => {
      expect(screen.getByText("Alice")).toBeInTheDocument();
    });
  });
});
