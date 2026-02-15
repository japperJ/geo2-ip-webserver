import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sitesApi, siteUsersApi, usersApi, authApi } from '../services/api'

interface SiteUser {
  id: string
  user_id: string
  role: string
  created_at: string
  user?: {
    username: string
    email: string
    full_name: string
  }
}

interface User {
  id: string
  username: string
  email: string
  full_name: string
}

export default function SiteUsers() {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const [siteUsers, setSiteUsers] = useState<SiteUser[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [site, setSite] = useState<any>(null)
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', full_name: '' })

  useEffect(() => {
    if (siteId) loadData()
  }, [siteId])

  const loadData = async () => {
    try {
      const [siteRes, usersRes] = await Promise.all([
        sitesApi.get(siteId!),
        usersApi.list(search),
      ])
      setSite(siteRes.data)
      setUsers(usersRes.data)
      
      const siteUsersRes = await siteUsersApi.list(siteId!)
      setSiteUsers(siteUsersRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const addUser = async (userId: string, role: string) => {
    try {
      await siteUsersApi.add(siteId!, { user_id: userId, role: role.toLowerCase() })
      setShowAdd(false)
      loadData()
    } catch (error) {
      console.error('Failed to add user:', error)
      alert('Failed to add user')
    }
  }

  const removeUser = async (siteUserId: string) => {
    if (!confirm('Remove this user from the site?')) return
    try {
      await siteUsersApi.delete(siteId!, siteUserId)
      loadData()
    } catch (error) {
      console.error('Failed to remove user:', error)
    }
  }

  const updateRole = async (siteUserId: string, role: string) => {
    try {
      await siteUsersApi.updateRole(siteId!, siteUserId, role.toLowerCase())
      loadData()
    } catch (error) {
      console.error('Failed to update role:', error)
    }
  }

  const createAndAddUser = async (role: string) => {
    if (!newUser.username || !newUser.email || !newUser.password) {
      alert('Please fill in all required fields')
      return
    }
    try {
      const createdUser = await authApi.createUser(newUser)
      await siteUsersApi.add(siteId!, { user_id: createdUser.data.id, role: role.toLowerCase() })
      setShowCreate(false)
      setNewUser({ username: '', email: '', password: '', full_name: '' })
      loadData()
      alert('User created and added to site!')
    } catch (error: any) {
      console.error('Failed to create user:', error)
      alert(error.response?.data?.detail || 'Failed to create user')
    }
  }

  const existingUserIds = siteUsers.map(su => su.user_id)

  if (loading) {
    return <div className="container">Loading...</div>
  }

  return (
    <div>
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate(`/sites/${siteId}`)}>
            Back
          </button>
          <h1>Manage Users - {site?.name}</h1>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => { setShowCreate(!showCreate); setShowAdd(false); }}>
            {showCreate ? 'Cancel' : '+ Create User'}
          </button>
          <button className="btn btn-primary" onClick={() => { setShowAdd(!showAdd); setShowCreate(false); }}>
            {showAdd ? 'Cancel' : '+ Add Existing User'}
          </button>
        </div>
      </header>

      <div className="container">
        {showCreate && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-header">
              <h2 className="card-title">Create New User & Add to Site</h2>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group">
                <label className="form-label">Username *</label>
                <input
                  type="text"
                  className="form-input"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email *</label>
                <input
                  type="email"
                  className="form-input"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password *</label>
                <input
                  type="password"
                  className="form-input"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                />
              </div>
            </div>
            <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label className="form-label" style={{ margin: 0 }}>Role:</label>
              <select className="form-select" style={{ width: 'auto' }} id="new-user-role">
                <option value="admin">Admin</option>
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
              </select>
              <button className="btn btn-primary" onClick={() => createAndAddUser((document.getElementById('new-user-role') as HTMLSelectElement).value)}>
                Create & Add
              </button>
            </div>
          </div>
        )}

        {showAdd && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-header">
              <h2 className="card-title">Add User to Site</h2>
            </div>
            <div className="form-group">
              <label className="form-label">Search Users</label>
              <input
                type="text"
                className="form-input"
                placeholder="Search by username or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {users
                .filter(u => !existingUserIds.includes(u.id))
                .map(user => (
                  <div key={user.id} style={{ 
                    padding: '12px', 
                    borderBottom: '1px solid #eee',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div><strong>{user.username}</strong></div>
                      <div style={{ fontSize: '12px', color: '#666' }}>{user.email}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <select 
                        className="form-select" 
                        style={{ width: 'auto' }}
                        id={`role-${user.id}`}
                        defaultValue="viewer"
                      >
                        <option value="admin">Admin</option>
                        <option value="editor">Editor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                      <button 
                        className="btn btn-primary"
                        onClick={() => addUser(user.id, (document.getElementById(`role-${user.id}`) as HTMLSelectElement).value)}
                      >
                        Add
                      </button>
                    </div>
                  </div>
                ))}
              {users.length === 0 && <div style={{ padding: '20px', textAlign: 'center' }}>No users found</div>}
            </div>
          </div>
        )}

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Site Users ({siteUsers.length})</h2>
          </div>
          
          {siteUsers.length === 0 ? (
            <div className="empty-state">No users assigned to this site yet</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Added</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {siteUsers.map(su => (
                  <tr key={su.id}>
                    <td>{su.user?.username || su.user_id}</td>
                    <td>{su.user?.email || '-'}</td>
                    <td>
                      <select
                        className="form-select"
                        style={{ width: 'auto' }}
                        value={su.role}
                        disabled={su.role === 'owner'}
                        onChange={(e) => updateRole(su.id, e.target.value)}
                      >
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="editor">Editor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                    <td>{new Date(su.created_at).toLocaleDateString()}</td>
                    <td>
                      {su.role !== 'owner' && (
                        <button 
                          className="btn btn-danger"
                          onClick={() => removeUser(su.id)}
                        >
                          Remove
                        </button>
                      )}
                    </td>
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
