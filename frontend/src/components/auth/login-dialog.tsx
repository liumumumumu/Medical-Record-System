import { CloseOutlined, LockOutlined, UserAddOutlined } from "@ant-design/icons";
import { useEffect, useId, useState, type FormEvent } from "react";
import type { RegisterRequest } from "../../types/medical-record";

type LoginDialogProps = {
  open: boolean;
  onClose: () => void;
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (request: RegisterRequest) => Promise<void>;
};

type DialogMode = "login" | "register";

export function LoginDialog({ open, onClose, onLogin, onRegister }: LoginDialogProps) {
  const usernameId = useId();
  const displayNameId = useId();
  const passwordId = useId();
  const confirmPasswordId = useId();
  const [mode, setMode] = useState<DialogMode>("login");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      setError("");
      setMode("login");
      return;
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  function switchMode(nextMode: DialogMode) {
    setMode(nextMode);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const username = String(formData.get("username") ?? "").trim();
    const password = String(formData.get("password") ?? "");
    const displayName = String(formData.get("displayName") ?? "").trim();
    const confirmPassword = String(formData.get("confirmPassword") ?? "");

    if (!username || !password || (mode === "register" && !displayName)) {
      setError("请完整填写必填信息。");
      return;
    }
    if (mode === "register" && !/^[A-Za-z0-9_]{3,30}$/.test(username)) {
      setError("用户名需为 3-30 位字母、数字或下划线。");
      return;
    }
    if (mode === "register" && (password.length < 6 || password.length > 72)) {
      setError("密码长度需为 6-72 位。");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError("两次输入的密码不一致。");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      if (mode === "login") await onLogin(username, password);
      else await onRegister({ username, password, displayName });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "请求失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  const isRegister = mode === "register";
  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <section aria-labelledby="account-title" aria-modal="true" className="login-dialog" onMouseDown={(event) => event.stopPropagation()} role="dialog">
        <button className="dialog-close" type="button" onClick={onClose} aria-label="关闭账户窗口"><CloseOutlined /></button>
        <span className="dialog-mark" aria-hidden="true">{isRegister ? <UserAddOutlined /> : <LockOutlined />}</span>
        <p className="section-kicker">Account Access</p>
        <h2 id="account-title">{isRegister ? "注册系统账号" : "登录系统"}</h2>
        <p className="dialog-description">{isRegister ? "账号将由后端保存并立即登录。课程演示请仅使用虚构或脱敏身份信息。" : "使用后端账号登录以创建、查看和下载属于当前用户的病例记录。"}</p>

        <div className="account-switch" role="tablist" aria-label="账户操作">
          <button className={mode === "login" ? "is-active" : ""} type="button" role="tab" aria-selected={mode === "login"} onClick={() => switchMode("login")}>登录</button>
          <button className={mode === "register" ? "is-active" : ""} type="button" role="tab" aria-selected={mode === "register"} onClick={() => switchMode("register")}>注册</button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor={usernameId}>账号</label>
          <input id={usernameId} name="username" type="text" autoComplete="username" placeholder="3-30 位字母、数字或下划线" autoFocus />
          {isRegister ? <><label htmlFor={displayNameId}>显示名称</label><input id={displayNameId} name="displayName" type="text" autoComplete="name" maxLength={30} placeholder="例如：王医生" /></> : null}
          <label htmlFor={passwordId}>密码</label>
          <input id={passwordId} name="password" type="password" autoComplete={isRegister ? "new-password" : "current-password"} placeholder={isRegister ? "6-72 位密码" : "请输入密码"} />
          {isRegister ? <><label htmlFor={confirmPasswordId}>确认密码</label><input id={confirmPasswordId} name="confirmPassword" type="password" autoComplete="new-password" placeholder="再次输入密码" /></> : null}
          {error ? <p className="form-status form-status--error" role="alert">{error}</p> : null}
          <button className="primary-button primary-button--wide" disabled={submitting} type="submit">{submitting ? "正在提交" : isRegister ? "注册并进入系统" : "进入系统"}</button>
        </form>
      </section>
    </div>
  );
}
