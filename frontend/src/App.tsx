import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { HashRouter,Routes, Route, Navigate, Outlet } from "react-router-dom";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import CreateTask from "./pages/CreateTask";
import RunAI from "./pages/RunAI";
import Logs from "./pages/Logs";
import Profile from "./pages/Profile";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const isAuthenticated = () => {
return !!localStorage.getItem("token");
};

// Protect dashboard routes
const PrivateRoute = () => {
return isAuthenticated() ? <Outlet /> : <Navigate to="/login" />;
};

// Redirect / to /login unless logged in
const RootRedirect = () => {
return isAuthenticated() ? <Navigate to="/dashboard" /> : <Navigate to="/login" />;
};

const App = () => (
<QueryClientProvider client={queryClient}>
<TooltipProvider>
<Toaster />
<Sonner />
<HashRouter>
<Routes>
{/* Root - redirect */}
<Route path="/" element={<RootRedirect />} />

      {/* Auth routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* Protected Routes */}
      <Route element={<PrivateRoute />}>
        <Route
          path="/dashboard"
          element={
            <DashboardLayout>
              <Dashboard />
            </DashboardLayout>
          }
        />
        <Route
          path="/tasks"
          element={
            <DashboardLayout>
              <Tasks />
            </DashboardLayout>
          }
        />
        <Route
          path="/create-task"
          element={
            <DashboardLayout>
              <CreateTask />
            </DashboardLayout>
          }
        />
        <Route
          path="/run-ai"
          element={
            <DashboardLayout>
              <RunAI />
            </DashboardLayout>
          }
        />
        <Route
          path="/logs"
          element={
            <DashboardLayout>
              <Logs />
            </DashboardLayout>
          }
        />
        <Route
          path="/profile"
          element={
            <DashboardLayout>
              <Profile />
            </DashboardLayout>
          }
        />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  </HashRouter>
</TooltipProvider>
</QueryClientProvider> );
export default App;