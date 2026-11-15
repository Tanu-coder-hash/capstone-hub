import React, { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function Feedback({ user }) {
  const [teams, setTeams] = useState([]);
  const [feedbackList, setFeedbackList] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const headers = {
    "Content-Type": "application/json",
    "x-user-id": String(user?.id || 20),
    "x-user-role": user?.role || "student",
  };

  const loadFeedback = async () => {
    setLoading(true);
    setError("");

    try {
      if (user?.role === "faculty") {
        const response = await fetch(
          `${API_BASE}/feedback/faculty/teams`,
          { headers }
        );

        if (!response.ok) {
          throw new Error("Unable to load your allocated teams.");
        }

        setTeams(await response.json());
      } else {
        const response = await fetch(`${API_BASE}/feedback/me`, {
          headers,
        });

        if (!response.ok) {
          throw new Error("Unable to load your feedback.");
        }

        setFeedbackList(await response.json());
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeedback();
  }, [user?.id, user?.role]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedTeam || feedbackText.trim().length < 5) {
      setError("Select a team and enter at least 5 characters of feedback.");
      return;
    }

    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/feedback/teams/${selectedTeam}`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            feedback: feedbackText.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to submit feedback.");
      }

      setMessage("Feedback submitted successfully!");
      setFeedbackText("");
      setSelectedTeam("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString) =>
    new Date(dateString).toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "short",
    });

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6 text-gray-500">
        Loading feedback...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Faculty Feedback
        </h1>
        <p className="text-gray-500 text-sm mt-2">
          {user?.role === "faculty"
            ? "Share feedback and guidance with your allocated project teams."
            : "View feedback and guidance provided by your faculty guide."}
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
          {message}
        </div>
      )}

      {user?.role === "faculty" ? (
        <>
          <div className="bg-white border rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-bold text-gray-800">
              Your Allocated Teams
            </h2>

            {teams.length === 0 ? (
              <p className="text-sm text-gray-500">
                No allocated teams have been assigned to you yet.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {teams.map((team) => (
                  <button
                    key={team.id}
                    type="button"
                    onClick={() => setSelectedTeam(String(team.id))}
                    className={`text-left border rounded-lg p-4 transition ${
                      selectedTeam === String(team.id)
                        ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-100"
                        : "border-gray-200 hover:border-indigo-300"
                    }`}
                  >
                    <p className="font-semibold text-gray-900">
                      {team.name || `Team #${team.id}`}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      Team ID: {team.id}
                      {team.semester ? ` · Semester ${team.semester}` : ""}
                    </p>
                    {selectedTeam === String(team.id) && (
                      <p className="text-xs text-indigo-600 font-semibold mt-2">
                        Selected
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {teams.length > 0 && (
            <form
              onSubmit={handleSubmit}
              className="bg-white border rounded-xl p-6 space-y-4"
            >
              <h2 className="text-xl font-bold text-gray-800">
                Submit Team Feedback
              </h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Selected Team
                </label>
                <select
                  value={selectedTeam}
                  onChange={(e) => setSelectedTeam(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  required
                >
                  <option value="">Choose an allocated team</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name || `Team #${team.id}`} (ID: {team.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Feedback
                </label>
                <textarea
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="Write your feedback, suggestions, and guidance for the team..."
                  rows={6}
                  minLength={5}
                  maxLength={5000}
                  className="w-full border rounded-lg px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
                <p className="text-xs text-gray-400 text-right mt-1">
                  {feedbackText.length}/5000 characters
                </p>
              </div>

              <button
                type="submit"
                disabled={submitting || !selectedTeam || feedbackText.trim().length < 5}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? "Submitting..." : "Submit Feedback"}
              </button>
            </form>
          )}
        </>
      ) : (
        <div className="bg-white border rounded-xl divide-y">
          <div className="p-5">
            <h2 className="text-xl font-bold text-gray-800">
              Feedback From Your Faculty
            </h2>
          </div>

          {feedbackList.length === 0 ? (
            <div className="p-10 text-center">
              <p className="text-2xl mb-3">📝</p>
              <p className="font-semibold text-gray-800">
                No feedback available yet
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Feedback from your faculty guide will appear here.
              </p>
            </div>
          ) : (
            feedbackList.map((item) => (
              <div key={item.id} className="p-5">
                <div className="flex justify-between flex-wrap gap-2">
                  <p className="font-semibold text-gray-800">
                    Team #{item.team_id}
                  </p>
                  <span className="text-xs text-gray-500">
                    {formatDate(item.created_at)}
                  </span>
                </div>

                <p className="text-sm text-gray-700 mt-3 whitespace-pre-wrap">
                  {item.feedback}
                </p>

                <p className="text-xs text-gray-400 mt-3">
                  Faculty ID: {item.faculty_id}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
