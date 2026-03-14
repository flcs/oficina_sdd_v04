import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios, { AxiosError } from "axios";

interface FormState {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

interface FieldErrors {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

function validate(values: FormState): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.currentPassword) {
    errors.currentPassword = "Senha atual é obrigatória";
  }
  if (!values.newPassword) {
    errors.newPassword = "Nova senha é obrigatória";
  } else if (values.newPassword.length < 8) {
    errors.newPassword = "A nova senha deve ter pelo menos 8 caracteres";
  }
  if (values.newPassword !== values.confirmPassword) {
    errors.confirmPassword = "As senhas não coincidem";
  }
  return errors;
}

export default function ChangeInitialPasswordPage(): React.ReactElement {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>): void {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    setServerError("");
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    const errors = validate(form);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    const token = sessionStorage.getItem("access_token");
    if (!token) {
      navigate("/login");
      return;
    }

    setLoading(true);
    setServerError("");
    try {
      await axios.post(
        "/auth/change-initial-password",
        {
          current_password: form.currentPassword,
          new_password: form.newPassword,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      navigate("/dashboard");
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      if (error.response?.status === 401) {
        setServerError("Senha atual incorreta ou sessão expirada.");
      } else if (error.response?.status === 503) {
        setServerError("Serviço temporariamente indisponível. Tente novamente em breve.");
      } else {
        setServerError("Não foi possível alterar a senha. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="change-password-page">
      <h1>Alterar senha inicial</h1>
      <p>Por segurança, você precisa alterar sua senha antes de continuar.</p>
      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="currentPassword">Senha atual</label>
          <input
            id="currentPassword"
            name="currentPassword"
            type="password"
            autoComplete="current-password"
            value={form.currentPassword}
            onChange={handleChange}
          />
          {fieldErrors.currentPassword && (
            <span role="alert">{fieldErrors.currentPassword}</span>
          )}
        </div>
        <div>
          <label htmlFor="newPassword">Nova senha</label>
          <input
            id="newPassword"
            name="newPassword"
            type="password"
            autoComplete="new-password"
            value={form.newPassword}
            onChange={handleChange}
          />
          {fieldErrors.newPassword && (
            <span role="alert">{fieldErrors.newPassword}</span>
          )}
        </div>
        <div>
          <label htmlFor="confirmPassword">Confirmar nova senha</label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={handleChange}
          />
          {fieldErrors.confirmPassword && (
            <span role="alert">{fieldErrors.confirmPassword}</span>
          )}
        </div>
        {serverError && (
          <div role="alert" className="server-error">
            {serverError}
          </div>
        )}
        <button type="submit" disabled={loading}>
          {loading ? "Salvando..." : "Alterar senha"}
        </button>
      </form>
    </main>
  );
}

export { ChangeInitialPasswordPage };
