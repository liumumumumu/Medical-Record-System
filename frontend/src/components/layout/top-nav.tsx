import { LockOutlined, LogoutOutlined } from "@ant-design/icons";
import { useState } from "react";
import { NavLink } from "react-router-dom";

type TopNavProps = {
  isLoggedIn: boolean;
  onLogin: () => void;
  onLogout: () => void;
};

export function TopNav({
  isLoggedIn,
  onLogin,
  onLogout,
}: TopNavProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <div className="brand-block">
          <span className="brand-kicker">Medical Demo Platform</span>
          <h1>医疗病历生成与分析系统</h1>
        </div>

        <div className="site-header__actions">
          <nav className="tab-bar" aria-label="主导航">
            <NavLink className={({ isActive }) => isActive ? "tab-link active" : "tab-link"} to="/upload">
              录入病例
            </NavLink>
            <NavLink className={({ isActive }) => isActive ? "tab-link active" : "tab-link"} to="/results">
              查看结果
            </NavLink>
          </nav>

          {isLoggedIn ? (
            <div className="account-menu">
              <button
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                className="avatar-button"
                onClick={() => setMenuOpen((current) => !current)}
                type="button"
              >
                <span className="avatar-placeholder">U</span>
              </button>
              {menuOpen ? (
                <div className="account-popover" role="menu">
                  <span>演示用户</span>
                  <button type="button" role="menuitem" onClick={() => { setMenuOpen(false); onLogout(); }}>
                    <LogoutOutlined />退出登录
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <button className="login-button" type="button" onClick={onLogin}>
              <LockOutlined />
              <span>登录</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
