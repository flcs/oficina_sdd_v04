/**
 * Frontend integration test: Login page displays 503 error and retry guidance.
 *
 * Validates that:
 *   - On 503 response, a message informing the user of unavailability is shown
 *   - The message hints that the user should try again later (retry guidance)
 *   - No internal error information (stack traces, DB errors) is exposed
 *
 * TDD: written before login_feedback.tsx (T048) and before any 503 handling
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

describe("LoginPage — 503 display and retry guidance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a service unavailability message on 503", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 503, data: { detail: "Service Unavailable" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "somepassword");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const alertText = screen.getByRole("alert").textContent?.toLowerCase() ?? "";
    // Should mention unavailability or asking to try again
    const retryIndicators = [
      "indisponível",
      "tente novamente",
      "try again",
      "unavailable",
      "momentaneamente",
      "temporariamente",
      "serviço",
    ];
    const hasRetryGuidance = retryIndicators.some((word) =>
      alertText.includes(word)
    );
    expect(hasRetryGuidance).toBe(true);
  });

  it("503 message does not expose internal error details", async () => {
    const LoginPage = await getLoginPage();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 503, data: { detail: "Service Unavailable" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "somepassword");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    const alertText = screen.getByRole("alert").textContent?.toLowerCase() ?? "";
    const internalLeaks = [
      "psycopg",
      "sql",
      "traceback",
      "database",
      "connection refused",
      "operationalerror",
    ];
    internalLeaks.forEach((leak) => {
      expect(alertText).not.toContain(leak);
    });
  });

  it("503 message is distinct from 401 message", async () => {
    const LoginPage = await getLoginPage();

    // Render for 401
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 401, data: { detail: "Credenciais inválidas" } },
    });

    const { unmount: unmount401 } = render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    const message401 = screen.getByRole("alert").textContent;
    unmount401();

    // Render for 503
    vi.clearAllMocks();
    mockedAxios.post = vi.fn().mockRejectedValue({
      response: { status: 503, data: { detail: "Service Unavailable" } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "somepassword");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    const message503 = screen.getByRole("alert").textContent;

    expect(message503).not.toBe(message401);
  });
});
