import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { auditApi } from '../services/api'

interface AuditLog {
  id: string
  timestamp: string
  client_ip: string
  ip_geo_country: string | null
  ip_geo_city: string | null
  client_gps_lat: string | null
  client_gps_lon: string | null
  decision: string
  reason: string | null
  user_agent: string | null
  artifact_s3_key: string | null
}

export default function AuditLogs() {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ decision: '', client_ip: '' })

  useEffect(() => {
    loadLogs()
  }, [siteId, filter])

  const loadLogs = async () => {
    try {
      const params: any = {}
      if (filter.decision) params.decision = filter.decision
      if (filter.client_ip) params.client_ip = filter.client_ip
      
      const response = await auditApi.list(siteId!, params)
      setLogs(response.data)
    } catch (error) {
      console.error('Failed to load audit logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const exportCsv = async () => {
    try {
      const params: any = {}
      if (filter.decision) params.decision = filter.decision
      
      const response = await auditApi.export(siteId!, params)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `audit-${siteId}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export CSV:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div>
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate(`/sites/${siteId}`)}>
            Back
          </button>
          <h1>Audit Logs</h1>
        </div>
        <button className="btn btn-primary" onClick={exportCsv}>
          Export CSV
        </button>
      </header>

      <div className="container">
        <div className="card">
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <select
              className="form-select"
              value={filter.decision}
              onChange={(e) => setFilter({ ...filter, decision: e.target.value })}
              style={{ width: '200px' }}
            >
              <option value="">All Decisions</option>
              <option value="allowed">Allowed</option>
              <option value="blocked">Blocked</option>
            </select>
            <input
              type="text"
              className="form-input"
              placeholder="Filter by IP..."
              value={filter.client_ip}
              onChange={(e) => setFilter({ ...filter, client_ip: e.target.value })}
              style={{ width: '200px' }}
            />
          </div>

          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : logs.length === 0 ? (
            <div className="empty-state">No audit logs found</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>IP Address</th>
                  <th>Location</th>
                  <th>GPS</th>
                  <th>Decision</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{formatDate(log.timestamp)}</td>
                    <td>{log.client_ip}</td>
                    <td>
                      {log.ip_geo_city && log.ip_geo_country
                        ? `${log.ip_geo_city}, ${log.ip_geo_country}`
                        : '-'}
                    </td>
                    <td>
                      {log.client_gps_lat && log.client_gps_lon
                        ? `${log.client_gps_lat}, ${log.client_gps_lon}`
                        : '-'}
                    </td>
                    <td>
                      <span className={`badge ${log.decision === 'allowed' ? 'badge-success' : 'badge-danger'}`}>
                        {log.decision}
                      </span>
                    </td>
                    <td>{log.reason || '-'}</td>
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
