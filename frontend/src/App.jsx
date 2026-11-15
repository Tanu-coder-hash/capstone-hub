import React, { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Navigate,
} from "react-router-dom";

import Teams from "./pages/Teams";
import Notifications from "./pages/Notifications";
import Feedback from "./pages/Feedback";
import NotificationBell from "./components/NotificationBell";

// Fallback Ideas component
function IdeasPage({ user }) {
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-3xl font-bold text-gray-800">
        Capstone Idea Bank & Voting
      </h1>

      <p className="text-gray-600">
        Logged in as{" "}
        <span className="font-semibold">{user.name}</span>{" "}
        (ID: {user.id}, Role: {user.role})
      </p>

      <div className="bg-white border rounded-lg p-6 shadow-sm">
        <p className="text-sm text-gray-500">
          Idea browsing, searching, upvoting, and submission components from Member 1.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const mockUsers = [
    { id: 1, name: "Student 1 (Team Leader)", role: "student" },
    { id: 2, name: "Student 2 (Team Member)", role: "student" },
    { id: 3, name: "Student 3 (Team Member)", role: "student" },
    { id: 10, name: "Prof. Faculty A", role: "faculty" },
  ];

  const [currentUser, setCurrentUser] = useState(mockUsers[0]);

  const navClass = ({ isActive }) =>
    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? "bg-indigo-50 text-indigo-700"
        : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
    }`;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 flex items-center justify-between gap-4 flex-wrap py-3">

            <div className="flex items-center gap-6">
              <span className="text-xl font-black tracking-tight text-indigo-700">
                CapstoneHub
              </span>

              <nav className="flex items-center gap-1 flex-wrap">
                <NavLink to="/ideas" className={navClass}>
                  Ideas
                </NavLink>

                <NavLink to="/teams" className={navClass}>
                  Teams
                </NavLink>

                <NavLink to="/notifications" className={navClass}>
                  Notifications
                </NavLink>

                <NavLink to="/feedback" className={navClass}>
                  Feedback
                </NavLink>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <NotificationBell user={currentUser} />

              <div className="flex items-center gap-2">
                <label
                  htmlFor="user-select"
                  className="text-xs font-semibold text-gray-500 uppercase hidden sm:block"
                >
                  Active User:
                </label>

                <select
                  id="user-select"
                  value={currentUser.id}
                  onChange={(e) => {
                    const selected = mockUsers.find(
                      (u) => u.id === parseInt(e.target.value)
                    );

                    if (selected) setCurrentUser(selected);
                  }}
                  className="text-sm bg-gray-50 border border-gray-300 rounded-md px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {mockUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} [{u.role}]
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/teams" replace />} />

            <Route
              path="/ideas"
              element={<IdeasPage user={currentUser} />}
            />

            <Route
              path="/teams"
              element={<Teams user={currentUser} />}
            />

            <Route
              path="/notifications"
              element={<Notifications user={currentUser} />}
            />

            <Route
              path="/feedback"
              element={<Feedback user={currentUser} />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
