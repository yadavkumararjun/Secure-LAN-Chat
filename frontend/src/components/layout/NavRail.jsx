import React from 'react';
import { MessageSquare, Users, Settings, Shield } from 'lucide-react';

/**
 * NavRail — Narrow 64px icon navigation column (leftmost panel).
 * Sections: Chats, Peers, Settings. Shows current user avatar at bottom.
 * All sections correspond to real existing features.
 */
export function NavRail({
  activeNav,
  onNavChange,
  currentUser,
  onOpenSettings,
}) {
  const navItems = [
    { id: 'chats',    icon: MessageSquare, label: 'Chats' },
    { id: 'peers',    icon: Users,         label: 'LAN Peers' },
    { id: 'settings', icon: Settings,      label: 'Settings' },
  ];

  return (
    <nav className="nav-rail" aria-label="Main navigation">
      {navItems.map(({ id, icon: Icon, label }) => (
        <button
          key={id}
          className={`nav-rail-item ${activeNav === id ? 'active' : ''}`}
          onClick={() => {
            if (id === 'settings') {
              onOpenSettings();
            } else {
              onNavChange(id);
            }
          }}
          aria-label={label}
          title={label}
        >
          <Icon size={20} />
          <span className="nav-rail-tooltip">{label}</span>
        </button>
      ))}

      <div className="nav-rail-spacer" />

      {/* Current user avatar */}
      <button
        className="nav-user-avatar"
        onClick={onOpenSettings}
        title={`${currentUser.name} — Settings & Profile`}
        aria-label="Open settings and profile"
      >
        {currentUser.avatar}
        <span className="nav-user-online-dot" aria-hidden="true" />
      </button>
    </nav>
  );
}
