import React, { useState } from "react";
import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import Teams from "./pages/Teams";

// Fallback Ideas component in case Member 1's page is imported differently
function IdeasPage({ user }) {
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-3xl font-bold text-gray-800">Capstone Idea Bank & Voting</h1>
      <p className="text-gray-600">
        Logged in as <span className="font-semibold">{user.name}</span> (ID: {user.id}, Role: {user.role})
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
  // Demo mock user profiles matching seed.py
  const mockUsers = [
    { id: 20, name: "Student 20 (Team Alpha Leader)", role: "student" },
    { id: 21, name: "Student 21 (Team Alpha Member)", role: "student" },
    { id: 30, name: "Student 30 (Team Beta Leader)", role: "student" },
    { id: 40, name: "Student 40 (Team Gamma Leader)", role: "student" },
    { id: 41, name: "Student 41 (Invited Student)", role: "student" },
    { id: 10, name: "Prof. Faculty A", role: "faculty" },
    { id: 11, name: "Prof. Faculty B", role: "faculty" },
  ];

  const [currentUser, setCurrentUser] = useState(mockUsers[0]);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
        {/* Navigation Bar */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            {/* Logo / Brand */}
            <div className="flex items-center space-x-8">
              <span className="text-xl font-black tracking-tight text-indigo-700">
                CapstoneHub
              </span>
              <nav className="flex space-x-4">
                <NavLink
                  to="/ideas"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                    }`
                  }
                >
                  Ideas
                </NavLink>
                <NavLink
                  to="/teams"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                    }`
                  }
                >
                  Teams
                </NavLink>
              </nav>
            </div>

            {/* Role / User Switcher for Viva Demo */}
            <div className="flex items-center space-x-3">
              <label htmlFor="user-select" className="text-xs font-semibold text-gray-500 uppercase">
                Active User:
              </label>
              <select
                id="user-select"
                value={currentUser.id}
                onChange={(e) => {
                  const selected = mockUsers.find((u) => u.id === parseInt(e.target.value));
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
        </header>

        {/* Main Content Area */}
        <main className="flex-1 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/teams" replace />} />
            <Route path="/ideas" element={<IdeasPage user={currentUser} />} />
            <Route path="/teams" element={<Teams user={currentUser} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}