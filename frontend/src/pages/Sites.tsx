import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { sitesApi } from '../services/api'
import { useAuthStore } from '../store/auth'

interface Site {
  id: string
  name: string
  hostname: string | null
  filter_mode: string
  created_at: string
}

export default function Sites() {
  const [sites, setSites] = useState<Site[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newSite, setNewSite] = useState({ name: '', hostname: '' })
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    loadSites()
  }, [])

  const loadSites = async () => {
    try {
      const response = await sitesApi.list()
      setSites(response.data)
    } catch (error) {
      console.error('Failed to load sites:', error)
    } finally {
      setLoading(false)
    }
  }

  const createSite = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await sitesApi.create(newSite)
      setShowCreate(false)
      setNewSite({ name: '', hostname: '' })
      loadSites()
    } catch (error) {
      console.error('Failed to create site:', error)
    }
  }

  const getFilterBadge = (mode: string) => {
    switch (mode) {
      case 'disabled':
        return <span className="badge badge-info">Disabled</span>
      case 'ip':
        return <span className="badge badge-warning">IP Only</span>
      case 'geo':
        return <span className="badge badge-success">Geo Only</span>
      case 'ip_and_geo':
        return <span className="badge badge-danger">IP + Geo</span>
      default:
        return <span className="badge">{mode}</span>
    }
  }

  return (
    <div>
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h1>Sites</h1>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            Logged in as: <strong>{user?.username}</strong> {user?.is_admin && '(Admin)'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/users')}>
            Users
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + New Site
          </button>
          <button className="btn btn-secondary" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <div className="container">
        {showCreate && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Create New Site</h2>
            </div>
            <form onSubmit={createSite}>
              <div className="form-group">
                <label className="form-label">Site Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={newSite.name}
                  onChange={(e) => setNewSite({ ...newSite, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Hostname (optional)</label>
                <input
                  type="text"
                  className="form-input"
                  value={newSite.hostname}
                  onChange={(e) => setNewSite({ ...newSite, hostname: e.target.value })}
                  placeholder="example.com"
                />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className="btn btn-primary">
                  Create
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="empty-state">Loading...</div>
        ) : sites.length === 0 ? (
          <div className="empty-state">
            <p>No sites yet. Create your first site to get started.</p>
          </div>
        ) : (
          <div className="sites-grid">
            {sites.map((site) => (
              <div
                key={site.id}
                className="card site-card"
                onClick={() => navigate(`/sites/${site.id}`)}
              >
                <div className="site-name">{site.name}</div>
                <div className="site-hostname">{site.hostname || 'No hostname'}</div>
                <div style={{ marginTop: '12px' }}>{getFilterBadge(site.filter_mode)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
