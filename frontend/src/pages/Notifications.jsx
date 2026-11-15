import React, { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function Notifications({ user }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const headers = {
    "Content-Type": "application/json",
    "x-user-id": String(user?.id || 20),
    "x-user-role": user?.role || "student",
  };

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/notifications`, { headers });

      if (!response.ok) {
        throw new Error("Unable to load notifications");
      }

      setNotifications(await response.json());
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, [user?.id, user?.role]);

  const markAsRead = async (id) => {
    try {
      const response = await fetch(
        `${API_BASE}/notifications/${id}/read`,
        { method: "PATCH", headers }
      );

      if (!response.ok) throw new Error("Could not update notification");

      await loadNotifications();
    } catch (err) {
      setError(err.message);
    }
  };

  const markAllAsRead = async () => {
    try {
      const response = await fetch(`${API_BASE}/notifications/read-all`, {
        method: "PATCH",
        headers,
      });

      if (!response.ok) throw new Error("Could not update notifications");

      await loadNotifications();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
          <p className="text-sm text-gray-500 mt-1">
            Stay updated on your teams and faculty feedback.
          </p>
        </div>

        {notifications.some((item) => !item.is_read) && (
          <button
            onClick={markAllAsRead}
            className="text-sm font-semibold text-indigo-600 hover:text-indigo-800"
          >
            Mark all as read
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading notifications...</p>
      ) : notifications.length === 0 ? (
        <div className="bg-white border rounded-xl p-12 text-center">
          <p className="text-3xl mb-3">🔔</p>
          <h2 className="font-semibold text-gray-800">You're all caught up!</h2>
          <p className="text-sm text-gray-500 mt-1">
            New updates will appear here.
          </p>
        </div>
      ) : (
        <div className="bg-white border rounded-xl divide-y">
          {notifications.map((item) => (
            <div
              key={item.id}
              className={`p-5 flex gap-4 ${
                item.is_read ? "" : "bg-indigo-50"
              }`}
            >
              <div className="text-2xl">
                {item.type === "FACULTY_FEEDBACK" ? "📝" : "📢"}
              </div>

              <div className="flex-1">
                <p className="text-sm text-gray-800">{item.message}</p>
                <p className="text-xs text-gray-500 mt-2">
                  Team #{item.team_id} ·{" "}
                  {new Date(item.created_at).toLocaleString()}
                </p>
                <p className="text-xs mt-1 font-medium text-gray-500">
                  {item.type.replaceAll("_", " ")}
                </p>
              </div>

              {!item.is_read && (
                <button
                  onClick={() => markAsRead(item.id)}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  Mark as read
                </button>
              )}

              {item.is_read && (
                <span className="text-xs text-gray-400">Read</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
