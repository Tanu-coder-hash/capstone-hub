import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = "http://localhost:8000/api/v1";

export default function NotificationBell({ user }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const headers = {
    "Content-Type": "application/json",
    "x-user-id": String(user?.id || 20),
    "x-user-role": user?.role || "student",
  };

  const loadNotifications = async () => {
    if (!user?.id) return;

    try {
      const [notificationsResponse, countResponse] = await Promise.all([
        fetch(`${API_BASE}/notifications`, { headers }),
        fetch(`${API_BASE}/notifications/unread-count`, { headers }),
      ]);

      if (!notificationsResponse.ok || !countResponse.ok) {
        throw new Error("Unable to load notifications");
      }

      const notificationData = await notificationsResponse.json();
      const countData = await countResponse.json();

      setNotifications(notificationData);
      setUnreadCount(countData.unread_count);
      setError("");
    } catch (err) {
      console.error("Notification loading error:", err);
      setError("Could not load notifications");
    }
  };

  useEffect(() => {
    loadNotifications();

    const interval = setInterval(loadNotifications, 30000);

    return () => clearInterval(interval);
  }, [user?.id, user?.role]);

  const markAsRead = async (notificationId) => {
    try {
      const response = await fetch(
        `${API_BASE}/notifications/${notificationId}/read`,
        {
          method: "PATCH",
          headers,
        }
      );

      if (!response.ok) {
        throw new Error("Could not mark notification as read");
      }

      await loadNotifications();
    } catch (err) {
      console.error(err);
      setError("Could not update notification");
    }
  };

  const markAllAsRead = async () => {
    try {
      const response = await fetch(`${API_BASE}/notifications/read-all`, {
        method: "PATCH",
        headers,
      });

      if (!response.ok) {
        throw new Error("Could not mark notifications as read");
      }

      await loadNotifications();
    } catch (err) {
      console.error(err);
      setError("Could not update notifications");
    }
  };

  const openNotification = async (notification) => {
    if (!notification.is_read) {
      await markAsRead(notification.id);
    }

    setIsOpen(false);

    if (notification.type === "FACULTY_FEEDBACK") {
      navigate("/feedback");
    } else {
      navigate("/teams");
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) loadNotifications();
        }}
        className="relative p-2 rounded-full text-gray-600 hover:bg-gray-100 hover:text-indigo-700 transition"
        aria-label="Notifications"
        aria-expanded={isOpen}
      >
        <span className="text-xl" aria-hidden="true">🔔</span>

        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-xs font-bold">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <button
            type="button"
            aria-label="Close notifications"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setIsOpen(false)}
          />

          <div className="absolute right-0 mt-3 w-80 sm:w-96 bg-white border border-gray-200 rounded-xl shadow-xl z-50 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div>
                <h3 className="font-bold text-gray-900">Notifications</h3>
                <p className="text-xs text-gray-500">
                  {unreadCount} unread
                </p>
              </div>

              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={markAllAsRead}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  Mark all as read
                </button>
              )}
            </div>

            {error && (
              <p className="px-4 py-2 text-sm text-red-600">{error}</p>
            )}

            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-2xl mb-2">🔕</p>
                  <p className="text-sm font-medium text-gray-700">
                    No notifications yet
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Updates will appear here.
                  </p>
                </div>
              ) : (
                notifications.map((notification) => (
                  <button
                    type="button"
                    key={notification.id}
                    onClick={() => openNotification(notification)}
                    className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 transition ${
                      notification.is_read ? "bg-white" : "bg-indigo-50"
                    }`}
                  >
                    <div className="flex gap-3">
                      <span className="text-lg">
                        {notification.type === "FACULTY_FEEDBACK"
                          ? "📝"
                          : "📢"}
                      </span>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800">
                          {notification.message}
                        </p>

                        <p className="text-xs text-gray-500 mt-1">
                          Team #{notification.team_id} ·{" "}
                          {formatDate(notification.created_at)}
                        </p>
                      </div>

                      {!notification.is_read && (
                        <span className="w-2 h-2 mt-1.5 rounded-full bg-indigo-600 flex-shrink-0" />
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>

            <div className="px-4 py-3 bg-gray-50 border-t">
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  navigate("/notifications");
                }}
                className="w-full text-sm font-semibold text-indigo-600 hover:text-indigo-800"
              >
                View all notifications
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
