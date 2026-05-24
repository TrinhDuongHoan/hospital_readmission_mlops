import { useEffect, useMemo, useState } from "react";
import { Ban, CheckCircle2, Edit3, RefreshCw, Save, UserPlus, X } from "lucide-react";
import { createUser, getUsers, setUserActive, updateUser } from "../services/api";

const emptyForm = {
  username: "",
  full_name: "",
  role: "doctor",
  password: "",
};

function formatRole(role) {
  return role === "admin" ? "Admin" : "Doctor";
}

export default function Users({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingUser, setEditingUser] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const isEditing = Boolean(editingUser);

  const sortedUsers = useMemo(
    () =>
      [...users].sort((left, right) => {
        if (left.is_active !== right.is_active) {
          return left.is_active ? -1 : 1;
        }

        if (left.role !== right.role) {
          return left.role === "admin" ? -1 : 1;
        }

        return left.username.localeCompare(right.username);
      }),
    [users]
  );

  async function loadUsers() {
    try {
      setLoading(true);
      setError("");

      const data = await getUsers(500);
      setUsers(data);
    } catch (err) {
      setError("Cannot load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function updateField(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function resetForm() {
    setForm(emptyForm);
    setEditingUser(null);
    setError("");
    setMessage("");
  }

  function startEdit(user) {
    setEditingUser(user);
    setForm({
      username: user.username,
      full_name: user.full_name || "",
      role: user.role,
      password: "",
    });
    setError("");
    setMessage("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setSaving(true);
      setError("");
      setMessage("");

      if (isEditing) {
        const payload = {
          full_name: form.full_name,
          role: form.role,
        };

        if (form.password.trim()) {
          payload.password = form.password;
        }

        await updateUser(editingUser.id, payload);
        setMessage(`Updated user ${editingUser.username}.`);
      } else {
        await createUser({
          username: form.username,
          full_name: form.full_name,
          role: form.role,
          password: form.password,
        });
        setMessage(`Created user ${form.username}.`);
      }

      setForm(emptyForm);
      setEditingUser(null);
      await loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Cannot save user.");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(user) {
    const nextActiveState = !user.is_active;
    const action = nextActiveState ? "enable" : "disable";
    const confirmed = window.confirm(`${action} user ${user.username}?`);

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setMessage("");

      await setUserActive(user.id, nextActiveState);
      setMessage(
        nextActiveState
          ? `Enabled user ${user.username}.`
          : `Disabled user ${user.username}.`
      );
      await loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Cannot update user status.");
    }
  }

  return (
    <section className="page">
      <div className="card form-card user-management-card">
        <div className="form-header">
          <div>
            <h3>{isEditing ? "Edit User" : "Create User"}</h3>
            <p>Manage doctor and admin accounts.</p>
          </div>

          {isEditing && (
            <button className="secondary-button" type="button" onClick={resetForm}>
              <X size={16} />
              Cancel
            </button>
          )}
        </div>

        {message && <div className="alert success">{message}</div>}
        {error && <div className="alert error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-grid user-form-grid">
            <label>
              <span>Username</span>
              <input
                disabled={isEditing}
                value={form.username}
                onChange={(event) => updateField("username", event.target.value)}
                required
              />
            </label>

            <label>
              <span>Full name</span>
              <input
                value={form.full_name}
                onChange={(event) => updateField("full_name", event.target.value)}
              />
            </label>

            <label>
              <span>Role</span>
              <select
                value={form.role}
                onChange={(event) => updateField("role", event.target.value)}
              >
                <option value="doctor">Doctor</option>
                <option value="admin">Admin</option>
              </select>
            </label>

            <label>
              <span>{isEditing ? "New password" : "Password"}</span>
              <input
                minLength={6}
                type="password"
                value={form.password}
                onChange={(event) => updateField("password", event.target.value)}
                placeholder={isEditing ? "Leave blank to keep current password" : ""}
                required={!isEditing}
              />
            </label>
          </div>

          <div className="form-actions">
            <button className="primary-button" disabled={saving} type="submit">
              {isEditing ? <Save size={16} /> : <UserPlus size={16} />}
              {saving ? "Saving..." : isEditing ? "Save Changes" : "Create User"}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <div className="table-header">
          <div>
            <h3>User Accounts</h3>
            <p>Doctors can manage patients; admins can operate the MLOps console.</p>
          </div>

          <button className="secondary-button" type="button" onClick={loadUsers}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading users...</div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Full Name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {sortedUsers.map((user) => {
                  const isCurrentUser = currentUser?.id === user.id;

                  return (
                    <tr key={user.id}>
                      <td>{user.id}</td>
                      <td>
                        <strong>{user.username}</strong>
                        {isCurrentUser && <span className="user-note">You</span>}
                      </td>
                      <td>{user.full_name || "N/A"}</td>
                      <td>
                        <span className={`role-pill ${user.role}`}>
                          {formatRole(user.role)}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`account-status-pill ${
                            user.is_active ? "active" : "disabled"
                          }`}
                        >
                          {user.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td>
                        {user.created_at
                          ? new Date(user.created_at).toLocaleString()
                          : "N/A"}
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="icon-button"
                            type="button"
                            onClick={() => startEdit(user)}
                            title="Edit user"
                          >
                            <Edit3 size={16} />
                          </button>

                          <button
                            className={`icon-button ${
                              user.is_active
                                ? "danger-icon-button"
                                : "success-icon-button"
                            }`}
                            disabled={isCurrentUser}
                            type="button"
                            onClick={() => handleStatusChange(user)}
                            title={user.is_active ? "Disable user" : "Enable user"}
                          >
                            {user.is_active ? (
                              <Ban size={16} />
                            ) : (
                              <CheckCircle2 size={16} />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {sortedUsers.length === 0 && (
                  <tr>
                    <td colSpan="7" className="empty-cell">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
