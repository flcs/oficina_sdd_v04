import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios, { AxiosError } from "axios";
import LoginFeedback, { LoginFeedbackVariant } from "../components/login_feedback";

interface LoginFormState {
  email: string;
  password: string;
}

interface FieldErrors {
  email?: string;
  password?: string;
}

interface LoginApiResponse {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
}

function validateForm(values: LoginFormState): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.email.trim()) {
    errors.email = "E-mail é obrigatório";
  } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.email.trim())) {
    errors.email = "E-mail inválido";
  }
  if (!values.password) {
    errors.password = "Senha é obrigatória";
  }
  return errors;
}

export default function LoginPage(): React.ReactElement {
  const navigate = useNavigate();
  const [form, setForm] = useState<LoginFormState>({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState<string>("");
  const [feedbackVariant, setFeedbackVariant] = useState<LoginFeedbackVariant>("neutral-error");
  const [loading, setLoading] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>): void {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    setServerError("");
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    const errors = validateForm(form);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setLoading(true);
    setServerError("");
    try {
      const response = await axios.post<LoginApiResponse>(
        "/auth/login",
        { email: form.email.trim().toLowerCase(), password: form.password },
        { headers: { "Content-Type": "application/json" } }
      );
      const { access_token, must_change_password } = response.data;
      sessionStorage.setItem("access_token", access_token);
      if (must_change_password) {
        navigate("/auth/change-initial-password");
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      if (error.response?.status === 503) {
        setFeedbackVariant("unavailable");
        setServerError(
          "Serviço temporariamente indisponível. Por favor, tente novamente em breve."
        );
      } else {
        setFeedbackVariant("neutral-error");
        setServerError(
          "Credenciais inválidas ou conta indisponível. Verifique e tente novamente."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <h1>Entrar</h1>
      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={handleChange}
            aria-describedby={fieldErrors.email ? "email-error" : undefined}
          />
          {fieldErrors.email && (
            <span id="email-error" role="alert">
              {fieldErrors.email}
            </span>
          )}
        </div>
        <div>
          <label htmlFor="password">Senha</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={handleChange}
            aria-describedby={fieldErrors.password ? "password-error" : undefined}
          />
          {fieldErrors.password && (
            <span id="password-error" role="alert">
              {fieldErrors.password}
            </span>
          )}
        </div>
        <LoginFeedback variant={feedbackVariant} visible={Boolean(serverError)} />
        <button type="submit" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}

export { LoginPage };
