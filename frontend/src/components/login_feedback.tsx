import React from "react";

export type LoginFeedbackVariant = "neutral-error" | "unavailable";

interface LoginFeedbackProps {
  /** Which feedback state to display. */
  variant: LoginFeedbackVariant;
  /** If true, the component is visible; if false, renders nothing. */
  visible: boolean;
}

const MESSAGES: Record<LoginFeedbackVariant, string> = {
  "neutral-error":
    "Email ou senha inválidos. Verifique os dados e tente novamente.",
  unavailable:
    "Serviço temporariamente indisponível. Tente novamente em breve.",
};

/**
 * LoginFeedback renders a neutral error or unavailability message for the
 * login page.
 *
 * Design rules:
 *   - "neutral-error" covers both wrong credentials AND account lockout (no
 *     lock disclosure — FR-002 anti-enumeration requirement).
 *   - "unavailable" covers 503 responses and guides the user to retry.
 */
export default function LoginFeedback({
  variant,
  visible,
}: LoginFeedbackProps): React.ReactElement | null {
  if (!visible) return null;
  return (
    <div role="alert" className={`login-feedback login-feedback--${variant}`}>
      {MESSAGES[variant]}
    </div>
  );
}

export { LoginFeedback };
