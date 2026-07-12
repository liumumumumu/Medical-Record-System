import { CloseOutlined, LockOutlined } from "@ant-design/icons";
import { useEffect, useId, useState, type FormEvent } from "react";

type LoginDialogProps = {
  open: boolean;
  onClose: () => void;
  onLogin: (username: string, password: string) => Promise<void>;
};

export function LoginDialog({ open, onClose, onLogin }: LoginDialogProps) {
  const emailId = useId();
  const passwordId = useId();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      setError("");
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const username = String(formData.get("username") ?? "").trim();
    const password = String(formData.get("password") ?? "");

    if (!username || !password) {
      setError("请输入账号和密码。");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await onLogin(username, password);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "登录失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <section
        aria-labelledby="login-title"
        aria-modal="true"
        className="login-dialog"
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
      >
        <button className="dialog-close" type="button" onClick={onClose} aria-label="关闭登录窗口">
          <CloseOutlined />
        </button>
        <span className="dialog-mark" aria-hidden="true"><LockOutlined /></span>
        <p className="section-kicker">Account Access</p>
        <h2 id="login-title">登录系统</h2>
        <p className="dialog-description">使用后端账号登录以创建、查看和下载属于当前用户的病例记录。</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor={emailId}>账号</label>
          <input id={emailId} name="username" type="text" autoComplete="username" placeholder="例如：doctor" autoFocus />
          <label htmlFor={passwordId}>密码</label>
          <input id={passwordId} name="password" type="password" autoComplete="current-password" placeholder="请输入密码" />
          {error ? <p className="form-status form-status--error" role="alert">{error}</p> : null}
          <button className="primary-button primary-button--wide" disabled={submitting} type="submit">{submitting ? "正在验证" : "进入系统"}</button>
        </form>
      </section>
    </div>
  );
}
