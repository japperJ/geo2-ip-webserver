import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/auth'
import { usersApi, authApi } from '../services/api'

interface User {
  id: string
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_admin: boolean
  created_at: string
}

export default function Users() {
  const { user } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [search, setSearch] = useState('')
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: ''
  })
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: ''
  })

  useEffect(() => {
    loadUsers()
  }, [search])

  const loadUsers = async () => {
    try {
      const res = await usersApi.list(search)
      setUsers(res.data)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await authApi.createUser(formData)
      setShowCreate(false)
      setFormData({ username: '', email: '', password: '', full_name: '' })
      loadUsers()
      alert('User created successfully!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create user')
    }
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await authApi.changePassword(passwordData.old_password, passwordData.new_password)
      setShowPassword(false)
      setPasswordData({ old_password: '', new_password: '' })
      alert('Password changed successfully!')
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to change password')
    }
  }

  if (loading) {
    return <div className="container">Loading...</div>
  }

  return (
    <div>
      <header className="header">
        <h1>User Management</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => setShowPassword(!showPassword)}>
            Change Password
          </button>
          {user?.is_admin && (
            <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
              {showCreate ? 'Cancel' : '+ Create User'}
            </button>
          )}
        </div>
      </header>

      <div className="container">
        {showPassword && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-header">
              <h2 className="card-title">Change Password</h2>
            </div>
            <form onSubmit={changePassword}>
              <div className="form-group">
                <label className="form-label">Current Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={passwordData.old_password}
                  onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">New Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Change Password</button>
            </form>
          </div>
        )}

        {showCreate && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-header">
              <h2 className="card-title">Create New User</h2>
            </div>
            <form onSubmit={createUser}>
              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  className="form-input"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Create User</button>
            </form>
          </div>
        )}

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">All Users</h2>
          </div>
          <div className="form-group">
            <input
              type="text"
              className="form-input"
              placeholder="Search users..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          {users.length === 0 ? (
            <div className="empty-state">No users found</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Full Name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.email}</td>
                    <td>{u.full_name || '-'}</td>
                    <td>{u.is_admin ? 'Admin' : 'User'}</td>
                    <td>{u.is_active ? 'Active' : 'Inactive'}</td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
