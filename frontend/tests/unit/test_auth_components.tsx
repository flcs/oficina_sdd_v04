/**
 * Frontend unit tests for authentication-related components:
 *   - LoginPage (login form behaviour)
 *   - LoginFeedback (feedback variants)
 *   - ChangeInitialPasswordPage (change password form)
 *
 * TDD T052 — Polish phase. All tests cover rendering, validation,
 * and user interaction at the component level.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import React from "react";

vi.mock("axios");

// ── LoginFeedback unit tests ───────────────────────────────────────────────────

describe("LoginFeedback", () => {
  const getComponent = async () => {
    const mod = await import("../../src/components/login_feedback");
    return mod.default ?? (mod as any).LoginFeedback;
  };

  it("renders nothing when visible=false", async () => {
    const LoginFeedback = await getComponent();
    const { container } = render(
      <LoginFeedback variant="neutral-error" visible={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders neutral error message when variant=neutral-error and visible=true", async () => {
    const LoginFeedback = await getComponent();
    render(<LoginFeedback variant="neutral-error" visible={true} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    const text = screen.getByRole("alert").textContent?.toLowerCase() ?? "";
    expect(text.length).toBeGreaterThan(0);
    // Must NOT contain lock-related words
    expect(text).not.toContain("bloqueado");
    expect(text).not.toContain("lock");
  });

  it("renders unavailability message when variant=unavailable and visible=true", async () => {
    const LoginFeedback = await getComponent();
    render(<LoginFeedback variant="unavailable" visible={true} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    const text = screen.getByRole("alert").textContent?.toLowerCase() ?? "";
    // Should include at least one of the expected retry indicators
    const indicators = [
      "indisponível",
      "tente novamente",
      "try again",
      "unavailable",
      "temporariamente",
    ];
    expect(indicators.some((i) => text.includes(i))).toBe(true);
  });

  it("neutral-error and unavailable show different messages", async () => {
    const LoginFeedback = await getComponent();

    const { unmount: unmount1 } = render(
      <LoginFeedback variant="neutral-error" visible={true} />
    );
    const neutralText = screen.getByRole("alert").textContent;
    unmount1();

    render(<LoginFeedback variant="unavailable" visible={true} />);
    const unavailText = screen.getByRole("alert").textContent;

    expect(neutralText).not.toBe(unavailText);
  });
});

// ── LoginPage unit tests ───────────────────────────────────────────────────────

describe("LoginPage — form validation", () => {
  const getLoginPage = async () => {
    const mod = await import("../../src/pages/login_page");
    return mod.default ?? (mod as any).LoginPage;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows validation error when email is empty on submit", async () => {
    const LoginPage = await getLoginPage();
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    // Leave email empty, fill password
    await userEvent.type(screen.getByLabelText(/senha|password/i), "somepassword");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
  });

  it("shows validation error when password is empty on submit", async () => {
    const LoginPage = await getLoginPage();
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
  });

  it("disables submit button while loading", async () => {
    const { default: axios } = await import("axios");
    const LoginPage = await getLoginPage();
    (axios.post as ReturnType<typeof vi.fn>) = vi.fn(
      () => new Promise(() => {}) // never resolves
    );

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), "admin@empresa.com");
    await userEvent.type(screen.getByLabelText(/senha|password/i), "somepassword");
    await userEvent.click(screen.getByRole("button", { name: /entrar|login|sign in/i }));

    await waitFor(() => {
      const button = screen.getByRole("button", { name: /salvando|loading|aguarde/i });
      expect(button).toBeDisabled();
    });
  });
});

// ── ChangeInitialPasswordPage unit tests ──────────────────────────────────────

describe("ChangeInitialPasswordPage — form validation", () => {
  const getPage = async () => {
    const mod = await import("../../src/pages/change_initial_password_page");
    return mod.default ?? (mod as any).ChangeInitialPasswordPage;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    sessionStorage.setItem("access_token", "test-token");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders current_password, new_password and confirm_password fields", async () => {
    const Page = await getPage();
    render(
      <MemoryRouter>
        <Page />
      </MemoryRouter>
    );
    expect(screen.getByLabelText(/senha atual|current.password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nova senha|new.password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirmar|confirm/i)).toBeInTheDocument();
  });

  it("shows validation error when new_password is shorter than 8 chars", async () => {
    const Page = await getPage();
    render(
      <MemoryRouter>
        <Page />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/senha atual|current.password/i), "admin");
    await userEvent.type(screen.getByLabelText(/nova senha|new.password/i), "short");
    await userEvent.type(screen.getByLabelText(/confirmar|confirm/i), "short");
    await userEvent.click(screen.getByRole("button", { name: /alterar|save|confirmar/i }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
  });

  it("shows validation error when passwords do not match", async () => {
    const Page = await getPage();
    render(
      <MemoryRouter>
        <Page />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/senha atual|current.password/i), "admin");
    await userEvent.type(screen.getByLabelText(/nova senha|new.password/i), "NewPass123");
    await userEvent.type(screen.getByLabelText(/confirmar|confirm/i), "DifferentPass");
    await userEvent.click(screen.getByRole("button", { name: /alterar|save|confirmar/i }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
  });
});
