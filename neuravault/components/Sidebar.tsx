"use client";

import {
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  usePathname,
} from "next/navigation";

import {
  UserButton,
  useUser,
} from "@clerk/nextjs";

import {
  BrainCircuit,
  Database,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Search,
  Upload,
  X,
} from "lucide-react";

const navigation = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    name: "AI Chat",
    href: "/chat",
    icon: MessageSquare,
  },
  {
    name: "Memories",
    href: "/memories",
    icon: Database,
  },
  {
    name: "Upload",
    href: "/upload",
    icon: Upload,
  },
];

export default function Sidebar() {
  const pathname =
    usePathname();

  const {
    user,
    isLoaded,
  } = useUser();

  const [
    mobileOpen,
    setMobileOpen,
  ] = useState(false);

  /*
   * Close the drawer whenever the user
   * navigates to another page.
   */
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  /*
   * Prevent background scrolling while
   * the mobile sidebar is open.
   */
  useEffect(() => {
    document.body.style.overflow =
      mobileOpen ? "hidden" : "";

    return () => {
      document.body.style.overflow =
        "";
    };
  }, [mobileOpen]);

  const userName =
    user?.fullName ||
    user?.firstName ||
    "NeuraVault User";

  const userEmail =
    user?.primaryEmailAddress
      ?.emailAddress || "";

  return (
    <>
      <button
        type="button"
        className="mobile-menu-button"
        onClick={() =>
          setMobileOpen(true)
        }
        aria-label="Open navigation"
        aria-expanded={mobileOpen}
      >
        <Menu size={23} />
      </button>

      <button
        type="button"
        className={`sidebar-overlay ${
          mobileOpen ? "visible" : ""
        }`}
        onClick={() =>
          setMobileOpen(false)
        }
        aria-label="Close navigation"
        tabIndex={
          mobileOpen ? 0 : -1
        }
      />

      <aside
        className={`sidebar ${
          mobileOpen
            ? "mobile-open"
            : ""
        }`}
      >
        <div className="sidebar-mobile-header">
          <span>Navigation</span>

          <button
            type="button"
            onClick={() =>
              setMobileOpen(false)
            }
            aria-label="Close navigation"
          >
            <X size={21} />
          </button>
        </div>

        <Link
          href="/"
          className="sidebar-logo"
        >
          <div className="logo-icon">
            <BrainCircuit
              size={25}
            />
          </div>

          <div className="sidebar-logo-text">
            <h2>NeuraVault</h2>
            <span>
              AI Knowledge System
            </span>
          </div>
        </Link>

        <nav className="sidebar-navigation">
          {navigation.map(
            (item) => {
              const Icon =
                item.icon;

              const isActive =
                pathname ===
                  item.href ||
                pathname.startsWith(
                  `${item.href}/`
                );

              return (
                <Link
                  href={item.href}
                  key={item.href}
                  className={`navigation-link ${
                    isActive
                      ? "active"
                      : ""
                  }`}
                >
                  <Icon size={20} />

                  <span>
                    {item.name}
                  </span>
                </Link>
              );
            }
          )}
        </nav>

        <Link
          href="/memories"
          className="sidebar-search"
        >
          <Search size={18} />

          <span>
            Search your vault
          </span>
        </Link>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <div className="status-indicator" />

            <div>
              <strong>
                AI System
              </strong>
              <span>Ready</span>
            </div>
          </div>

          <div className="sidebar-user">
            <UserButton
              appearance={{
                elements: {
                  avatarBox:
                    "sidebar-user-avatar",
                },
              }}
            />

            <div className="sidebar-user-information">
              <strong>
                {isLoaded
                  ? userName
                  : "Loading..."}
              </strong>

              {isLoaded &&
                userEmail && (
                  <span>
                    {userEmail}
                  </span>
                )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}