import React, { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function Teams({ user }) {
  const [team, setTeam] = useState(null);
  const [invites, setInvites] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [approvedIdeas, setApprovedIdeas] = useState([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [inviteUserId, setInviteUserId] = useState("");
  const [selectedIdeas, setSelectedIdeas] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const headers = {
    "Content-Type": "application/json",
    "x-user-id": String(user?.id || 20),
    "x-user-role": user?.role || "student",
  };

  const loadData = async () => {
    setError("");
    setMessage("");

    if (user?.role === "student") {
      try {
        const res = await fetch(`${API_BASE}/teams/me`, { headers });
        if (res.ok) {
          setTeam(await res.json());
        } else {
          setTeam(null);
        }
      } catch (e) {
        setTeam(null);
      }

      try {
        const res = await fetch(`${API_BASE}/teams/invites/me`, { headers });
        if (res.ok) setInvites(await res.json());
      } catch (e) {
        console.error(e);
      }

      try {
        const res = await fetch(`${API_BASE}/ideas?status=approved`, { headers });
        if (res.ok) setApprovedIdeas(await res.json());
      } catch (e) {
        console.error(e);
      }
    } else if (user?.role === "faculty") {
      try {
        const res = await fetch(`${API_BASE}/teams/idea-requests/pending`, { headers });
        if (res.ok) setPendingRequests(await res.json());
      } catch (e) {
        console.error(e);
      }
    }
  };

  useEffect(() => {
    loadData();
  }, [user]);

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    setError("");
    const res = await fetch(`${API_BASE}/teams`, {
      method: "POST",
      headers,
      body: JSON.stringify({ name: newTeamName }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Failed to create team");
    } else {
      setMessage("Team created successfully!");
      setNewTeamName("");
      loadData();
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!team) return;
    setError("");
    const res = await fetch(`${API_BASE}/teams/${team.id}/invites`, {
      method: "POST",
      headers,
      body: JSON.stringify({ user_id: parseInt(inviteUserId) }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Failed to send invitation");
    } else {
      setMessage(`Invited user ${inviteUserId} successfully!`);
      setInviteUserId("");
      loadData();
    }
  };

  const handleRespondInvite = async (inviteId, accept) => {
    setError("");
    const res = await fetch(`${API_BASE}/teams/invites/${inviteId}/respond`, {
      method: "POST",
      headers,
      body: JSON.stringify({ accept }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Error responding to invite");
    } else {
      setMessage(accept ? "Accepted invitation!" : "Rejected invitation.");
      loadData();
    }
  };

  const handleRequestIdeas = async (e) => {
    e.preventDefault();
    if (!team || selectedIdeas.length === 0) return;
    setError("");
    const res = await fetch(`${API_BASE}/teams/${team.id}/idea-requests`, {
      method: "POST",
      headers,
      body: JSON.stringify({ idea_ids: selectedIdeas }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Failed to submit preferences");
    } else {
      setMessage("Submitted preferences successfully!");
      loadData();
    }
  };

  const handleApprove = async (requestId) => {
    setError("");
    const res = await fetch(`${API_BASE}/teams/idea-requests/${requestId}/approve`, {
      method: "PATCH",
      headers,
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Failed to approve request");
    } else {
      setMessage("Idea successfully allocated to the team!");
      loadData();
    }
  };

  const handleReject = async (requestId) => {
    setError("");
    const res = await fetch(`${API_BASE}/teams/idea-requests/${requestId}/reject`, {
      method: "PATCH",
      headers,
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail || "Failed to reject request");
    } else {
      setMessage("Request rejected.");
      loadData();
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <h1 className="text-3xl font-bold text-gray-800">Team Formation & Allocation</h1>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-lg">{error}</div>}
      {message && <div className="p-4 bg-green-100 text-green-700 rounded-lg">{message}</div>}

      {user?.role === "student" && (
        <div className="space-y-6">
          {invites.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-5">
              <h2 className="text-lg font-semibold text-amber-900 mb-3">Pending Invitations</h2>
              <div className="space-y-3">
                {invites.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between bg-white p-3 rounded shadow-sm">
                    <span className="font-medium text-gray-800">Invited to join: {inv.team_name}</span>
                    <div className="space-x-2">
                      <button
                        onClick={() => handleRespondInvite(inv.id, true)}
                        className="px-3 py-1 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => handleRespondInvite(inv.id, false)}
                        className="px-3 py-1 bg-red-600 text-white text-sm font-semibold rounded hover:bg-red-700"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {team ? (
            <div className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
              <div className="flex justify-between items-center border-b pb-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{team.name}</h2>
                  <p className="text-sm text-gray-500">Semester: {team.semester}</p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                    team.status === "allocated"
                      ? "bg-green-100 text-green-800"
                      : team.status === "complete"
                      ? "bg-blue-100 text-blue-800"
                      : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {team.status}
                </span>
              </div>

              <div>
                <h3 className="text-md font-semibold text-gray-700 mb-2">Team Members ({team.members.length}/4)</h3>
                <ul className="divide-y divide-gray-100">
                  {team.members.map((m) => (
                    <li key={m.id} className="py-2 flex justify-between text-sm">
                      <span className="text-gray-800">
                        Student ID: {m.user_id} {m.user_id === team.leader_id && "(Leader)"}
                      </span>
                      <span className="font-semibold text-gray-500 capitalize">{m.status}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {team.leader_id === user?.id && team.status !== "allocated" && team.members.length < 4 && (
                <form onSubmit={handleInvite} className="pt-4 border-t flex gap-3">
                  <input
                    type="number"
                    placeholder="Student User ID"
                    value={inviteUserId}
                    onChange={(e) => setInviteUserId(e.target.value)}
                    className="border rounded px-3 py-2 text-sm w-48"
                    required
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-semibold hover:bg-indigo-700"
                  >
                    Invite Student
                  </button>
                </form>
              )}

              {team.leader_id === user?.id && team.status === "complete" && (
                <div className="pt-4 border-t space-y-3">
                  <h3 className="text-md font-semibold text-gray-800">Select Project Preferences (Up to 3)</h3>
                  <form onSubmit={handleRequestIdeas} className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {[0, 1, 2].map((idx) => (
                        <select
                          key={idx}
                          className="border rounded p-2 text-sm"
                          value={selectedIdeas[idx] || ""}
                          onChange={(e) => {
                            const updated = [...selectedIdeas];
                            const val = parseInt(e.target.value);
                            if (val) updated[idx] = val;
                            else updated.splice(idx, 1);
                            setSelectedIdeas(updated.filter(Boolean));
                          }}
                        >
                          <option value="">Preference #{idx + 1}</option>
                          {approvedIdeas.map((idea) => (
                            <option key={idea.id} value={idea.id}>
                              {idea.title} ({idea.domain})
                            </option>
                          ))}
                        </select>
                      ))}
                    </div>
                    <button
                      type="submit"
                      disabled={selectedIdeas.length === 0}
                      className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
                    >
                      Submit Idea Preferences
                    </button>
                  </form>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
              <h2 className="text-xl font-bold text-gray-800">You are not in a team</h2>
              <form onSubmit={handleCreateTeam} className="flex gap-3">
                <input
                  type="text"
                  placeholder="Enter Team Name (e.g. Team Alpha)"
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  className="border rounded px-3 py-2 text-sm flex-1"
                  required
                />
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 text-white rounded text-sm font-semibold hover:bg-indigo-700"
                >
                  Create Team
                </button>
              </form>
            </div>
          )}
        </div>
      )}

      {user?.role === "faculty" && (
        <div className="bg-white border rounded-lg p-6 shadow-sm space-y-4">
          <h2 className="text-xl font-bold text-gray-800">Pending Student Idea Requests</h2>
          {pendingRequests.length === 0 ? (
            <p className="text-sm text-gray-500">No pending allocation requests for your ideas.</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {pendingRequests.map((req) => (
                <div key={req.id} className="py-4 flex justify-between items-center">
                  <div>
                    <p className="font-semibold text-gray-800">Idea ID: {req.idea_id}</p>
                    <p className="text-xs text-gray-500">
                      Team #{req.team_id} (Preference #{req.preference})
                    </p>
                  </div>
                  <div className="space-x-2">
                    <button
                      onClick={() => handleApprove(req.id)}
                      className="px-4 py-1.5 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700"
                    >
                      Approve & Allocate
                    </button>
                    <button
                      onClick={() => handleReject(req.id)}
                      className="px-4 py-1.5 bg-red-600 text-white text-sm font-semibold rounded hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}