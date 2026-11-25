import { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  BarChart3,
  BookOpen,
  FileText,
  LayoutGrid,
  Menu,
  MessageSquare,
  PlusSquare,
  Settings,
  X,
} from 'lucide-react';
import { api } from '../services/api';

const MAIN_NAV = [
  { to: '/', label: 'Overview', icon: LayoutGrid },
  { to: '/build', label: 'Build Agent', icon: PlusSquare },
  { to: '/playground', label: 'Playground', icon: MessageSquare },
  { to: '/evaluations', label: 'Evaluations', icon: BarChart3 },
  { to: '/reports', label: 'Reports', icon: FileText },
];

const SECONDARY_NAV = [
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/docs', label: 'Documentation', icon: BookOpen },
];

export function AppLayout() {
  const [open, setOpen] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const check = () => {
      api
        .health()
        .then(() => active && setHealthy(true))
        .catch(() => active && setHealthy(false));
    };
    check();
    const timer = setInterval(check, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
      isActive
        ? 'bg-[#EAE5DC] text-[#292724] font-medium'
        : 'text-[#78756F] hover:bg-[#EAE5DC]/60 hover:text-[#292724]'
    }`;

  return (
    <div className="min-h-screen flex bg-[#FAF9F5] text-[#292724]">
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/20 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-60 bg-[#F3F1EB] border-r border-[#E4E0D8] flex flex-col justify-between transition-transform duration-150 lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div>
          <div className="h-14 px-4 flex items-center justify-between border-b border-[#E4E0D8]">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#C96442]" />
              <span className="font-serif-heading text-lg font-medium tracking-tight text-[#292724]">
                ForgeAI
              </span>
            </div>
            <button
              className="lg:hidden p-1 text-[#78756F] hover:text-[#292724]"
              onClick={() => setOpen(false)}
              aria-label="Close navigation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <nav className="p-3 space-y-1">
            {MAIN_NAV.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={navLinkClass}
                  onClick={() => setOpen(false)}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="p-3 border-t border-[#E4E0D8] space-y-1">
          {SECONDARY_NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={navLinkClass}
                onClick={() => setOpen(false)}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}

          <div className="pt-2 mt-2 border-t border-[#E4E0D8] px-3 py-1.5 flex items-center gap-2 text-xs text-[#78756F]">
            <span
              className={`w-2 h-2 rounded-full ${
                healthy === true
                  ? 'bg-emerald-600'
                  : healthy === false
                  ? 'bg-red-600'
                  : 'bg-[#78756F]'
              }`}
            />
            <span>
              {healthy === true
                ? 'Backend connected'
                : healthy === false
                ? 'Backend offline'
                : 'Checking backend'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-[#E4E0D8] bg-[#FAF9F5] px-4 lg:px-8 flex items-center justify-between lg:hidden">
          <button
            className="p-1.5 rounded-md border border-[#E4E0D8] text-[#292724]"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="w-4 h-4" />
          </button>
          <span className="font-serif-heading text-base font-medium">ForgeAI</span>
          <div className="w-7" />
        </header>

        <main className="flex-1 p-6 lg:p-8 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

