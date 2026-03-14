/**
 * Frontend integration test: Login page submit, token receipt and redirect.
 *
 * TDD: written before the login_page.tsx implementation (T025).
 * Uses Vitest + React Testing Library.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";

vi.mock("axios");
const mockedAxios = vi.mocked(axios, true);

// Dynamic import so the test file compiles even before the module exists
const getLoginPage = async () => {
  const mod = await import("../../src/pages/login_page");
  return mod.default ?? mod.LoginPage;
};

describe("LoginPage — integration flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders email and password fields with a submit button", async () => {
    const LoginPage = await getLoginPage();
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/senha|password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /entrar|login|sign in/i })
    ).toBeInTheDocument();
  });

  it("calls POST /auth/login with email and password on submit", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockResolvedValue({
      data: { access_token: "test-token", token_type: "bearer" },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "valid@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "secret");
    fireEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/auth/login",
        { email: "valid@empresa.com", password: "secret" },
        expect.any(Object)
      );
    });
  });

  it("stores the received token after successful login", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockResolvedValue({
      data: { access_token: "test-token", token_type: "bearer" },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "valid@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "secret");
    fireEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      const stored =
        sessionStorage.getItem("access_token") ||
        localStorage.getItem("access_token");
      expect(stored).toBe("test-token");
    });
  });

  it("shows inline validation error when email is empty on submit", async () => {
    const LoginPage = await getLoginPage();
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/email.*obrigat|email.*required/i)
      ).toBeInTheDocument();
    });
    expect(mockedAxios.post).not.toHaveBeenCalled();
  });
});
