import { CloseOutlined, LockOutlined } from "@ant-design/icons";
import { useEffect, useId, useState, type FormEvent } from "react";

type LoginDialogProps = {
  open: boolean;
  onClose: () => void;
  onLogin: () => void;
};

export function LoginDialog({ open, onClose, onLogin }: LoginDialogProps) {
  const emailId = useId();
  const passwordId = useId();
  const [error, setError] = useState("");

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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");

    if (!email || !password) {
      setError("请输入账号和密码。演示版本不会向服务器发送这些信息。");
      return;
    }

    onLogin();
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
        <p className="dialog-description">当前为前端演示登录，输入任意非空账号和密码即可查看登录状态。</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor={emailId}>账号</label>
          <input id={emailId} name="email" type="text" autoComplete="username" placeholder="请输入账号" autoFocus />
          <label htmlFor={passwordId}>密码</label>
          <input id={passwordId} name="password" type="password" autoComplete="current-password" placeholder="请输入密码" />
          {error ? <p className="form-status form-status--error" role="alert">{error}</p> : null}
          <button className="primary-button primary-button--wide" type="submit">进入系统</button>
        </form>
      </section>
    </div>
  );
}
