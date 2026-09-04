import { useEffect } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, ListChecks, LogOut, Rewind, Search } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useHealth } from "@/hooks/queries";
import { OfflineDatasetBadge, DemoModeBadge } from "@/components/badges";
import { WatchlistSelector } from "@/components/WatchlistSelector";
import { useActiveWatchlist } from "@/hooks/useActiveWatchlist";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const NAV = [
  { to: "/", label: "Investigation Room", icon: LayoutDashboard, end: true },
  { to: "/watchlists", label: "Watchlists", icon: ListChecks, end: false },
  { to: "/time-machine", label: "Time Machine", icon: Rewind, end: false },
  { to: "/stocks", label: "Stocks", icon: Search, end: false },
];

export function AppLayout() {
  const { user, loading, logout } = useAuth();
  const { data: health } = useHealth();
  const { activeId, setActive } = useActiveWatchlist();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [loading, user, navigate]);

  if (loading || !user) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Skeleton className="h-8 w-40" />
      </div>
    );
  }

  const initials = user.name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <Link to="/" className="flex items-center gap-2 px-1 py-1.5">
            <img src="/detective.svg" alt="" className="size-6 shrink-0" />
            <div className="leading-tight group-data-[collapsible=icon]:hidden">
              <div className="text-sm font-semibold tracking-tight">Market Detective</div>
              <div className="text-xs text-muted-foreground">We investigated why.</div>
            </div>
          </Link>
        </SidebarHeader>
        <SidebarSeparator />
        <SidebarContent>
          <SidebarGroup>
            <SidebarMenu>
              {NAV.map(({ to, label, icon: Icon, end }) => {
                const active = end ? pathname === to : pathname.startsWith(to);
                return (
                  <SidebarMenuItem key={to}>
                    <SidebarMenuButton
                      isActive={active}
                      tooltip={label}
                      render={<NavLink to={to} end={end} />}
                    >
                      <Icon />
                      <span>{label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <div className="flex flex-col gap-1.5 group-data-[collapsible=icon]:hidden">
            <div className="flex flex-wrap gap-1.5">
              <OfflineDatasetBadge label={health?.dataset_label} />
              <DemoModeBadge />
            </div>
            <p className="text-[11px] leading-snug text-muted-foreground">
              Educational prototype. Synthetic data — not live market data. Not investment advice.
            </p>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center gap-2 border-b bg-background/95 px-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <SidebarTrigger />
          <div className="ml-auto flex items-center gap-2">
            <WatchlistSelector activeId={activeId} onChange={setActive} />
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button variant="ghost" size="sm" className="gap-2">
                    <Avatar className="size-5">
                      <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline">{user.name}</span>
                  </Button>
                }
              />
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel>
                  <div className="font-medium text-foreground">{user.name}</div>
                  <div className="text-muted-foreground">{user.email}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  <LogOut />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <div className="min-h-0 flex-1 p-4 lg:p-6">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
