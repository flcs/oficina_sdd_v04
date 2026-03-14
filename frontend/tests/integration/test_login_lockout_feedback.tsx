/**
 * Frontend integration test: Login page displays neutral failure message.
 *
 * Validates that:
 *   - On 401 response, a neutral error message is shown (no lockout disclosure)
 *   - On multiple failed attempts (all returning 401), the message remains neutral
 *   - No message contains words that hint at account lockout or enumeration
 *
 * TDD: written before login_feedback.tsx (T048) and before any lockout
 * changes to login_page.tsx.
 * Uses Vitest + React Testing Library.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";

vi.mock("axios");
const mockedAxios = vi.mocked(axios, true);

const getLoginPage = async () => {
  const mod = await import("../../src/pages/login_page");
  return mod.default ?? (mod as any).LoginPage;
};

describe("LoginPage — lockout neutral feedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a neutral error message on 401 — no lockout disclosure", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Credenciais inválidas" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "locked@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const alertText = screen.getByRole("alert").textContent?.toLowerCase() ?? "";
    const lockoutWords = ["bloqueado", "lock", "too many", "tentativas", "muitas"];
    lockoutWords.forEach((word) => {
      expect(alertText).not.toContain(word);
    });
  });

  it("shows same neutral message regardless of whether account is locked", async () => {
    const LoginPage = await getLoginPage();

    // Simulate 401 for regular wrong password
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Credenciais inválidas" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "wrong1");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const firstMessage = screen.getByRole("alert").textContent;

    // Now simulate 401 for locked account (same HTTP status, neutral policy)
    vi.clearAllMocks();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Credenciais inválidas" } },
    });

    // Clear field and try again
    const passwordField = screen.getByLabelText(/senha|password/i);
    await userEvent.clear(passwordField);
    await userEvent.type(passwordField, "wrong2");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const secondMessage = screen.getByRole("alert").textContent;
    // Both should be identical neutral messages
    expect(firstMessage).toBe(secondMessage);
  });

  it("clears error message when user starts typing again", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Credenciais inválidas" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    // Start typing in the password field — error should clear
    await userEvent.type(screen.getByLabelText(/senha|password/i), "X");

    await waitFor(() => {
      const alert = screen.queryByRole("alert");
      // Alert should either be gone or have empty text
      if (alert) {
        expect(alert.textContent).toBe("");
      }
    });
  });
});
