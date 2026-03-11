import { NavLink, Outlet } from 'react-router-dom'
import './dashboard.css'

export function DashboardLayout() {
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <div className="brand-logo">NA</div>
          <div className="brand-title">
            <div className="brand-name">NovelAgent</div>
            <div className="brand-sub">编辑部控制台</div>
          </div>
        </div>

        <nav className="nav">
          <div className="nav-group">工作台</div>
          <NavLink to="/projects" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            项目
          </NavLink>
          <NavLink to="/studio" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            分部大纲 Studio
          </NavLink>
          <div className="nav-group">知识库</div>
          <NavLink to="/roles" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
            角色学习笔记
          </NavLink>
        </nav>

        <div className="side-footer">
          <div className="pill">浅蓝主题 · v0</div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <div className="topbar-title">小说编辑部 Agent</div>
            <div className="topbar-desc">需求 → 初纲 → 角色细化 → 汇总 → 确认 → 写作</div>
          </div>
          <div className="topbar-right">{/* reserved */}</div>
        </header>

        <div className="contentWrap">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

