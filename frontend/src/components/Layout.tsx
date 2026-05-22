import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Globe, Search, FileText, Shield, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/targets', label: 'Target', icon: Globe, end: false },
  { to: '/scans', label: 'Scansioni', icon: Search, end: false },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-[#0a0f1e]">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-[#0d1424] border-r border-[#1f2937] flex flex-col z-10">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-[#1f2937]">
          <div className="flex items-center justify-center w-9 h-9 bg-cyan-500/10 rounded-lg border border-cyan-500/30">
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-cyan-400">PentaShield</span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded uppercase tracking-wider">
              Beta
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative ${
                  isActive
                    ? 'text-cyan-400 bg-cyan-500/10 border-l-2 border-cyan-400 pl-[10px]'
                    : 'text-gray-400 hover:text-white hover:bg-[#1f2937]'
                }`
              }
            >
              <Icon className="w-4.5 h-4.5 w-5 h-5 flex-shrink-0" />
              {label}
            </NavLink>
          ))}

          <NavLink
            to="/scans"
            className="hidden"
          />

          {/* Reports link — goes to scans (reports are per-scan) */}
          <NavLink
            to="/scans"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative ${
                isActive
                  ? 'text-cyan-400 bg-cyan-500/10'
                  : 'text-gray-400 hover:text-white hover:bg-[#1f2937]'
              }`
            }
            style={{ display: 'none' }}
          >
            <FileText className="w-5 h-5 flex-shrink-0" />
            Report
          </NavLink>
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-[#1f2937]">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs text-gray-500 truncate">{user?.email ?? '—'}</p>
              <p className="text-xs text-gray-600 mt-0.5 capitalize">{user?.plan ?? 'free'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-gray-500 hover:text-red-400 transition-colors px-2 py-1.5 rounded-lg hover:bg-red-900/20 flex-shrink-0"
              title="Disconnetti"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 flex-1 min-h-screen overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
