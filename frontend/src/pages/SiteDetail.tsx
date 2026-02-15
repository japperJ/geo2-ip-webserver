import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { MapContainer, TileLayer, Polygon, Circle, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { sitesApi, geofencesApi, ipRulesApi } from '../services/api'

type FilterMode = 'disabled' | 'ip' | 'geo' | 'ip_and_geo'

interface Geofence {
  id: string
  name: string | null
  polygon: any
  center_lat: string | null
  center_lon: string | null
  radius_meters: string | null
}

interface IPRule {
  id: string
  cidr: string
  action: string
  description: string | null
  is_active: boolean
  priority: number
}

interface Site {
  id: string
  name: string
  hostname: string | null
  filter_mode: FilterMode
  block_page_title: string
  block_page_message: string
}

function MapDrawer({ 
  geofence, 
  onCenterClick,
  onPolygonDraw 
}: { 
  geofence: Geofence | null; 
  onCenterClick?: (lat: number, lon: number) => void;
  onPolygonDraw?: (coords: [number, number][]) => void;
}) {
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([])
  
  useMapEvents({
    click: (e) => {
      if (geofence?.polygon || (geofence?.center_lat && geofence?.center_lon && geofence?.radius_meters)) {
        return
      }
      
      if (onCenterClick) {
        onCenterClick(e.latlng.lat, e.latlng.lng)
      }
      
      if (onPolygonDraw) {
        const newPoint: [number, number] = [e.latlng.lat, e.latlng.lng]
        
        if (polygonPoints.length > 0) {
          const lastPoint = polygonPoints[polygonPoints.length - 1]
          const dist = Math.sqrt(
            Math.pow(newPoint[0] - lastPoint[0], 2) + 
            Math.pow(newPoint[1] - lastPoint[1], 2)
          )
          if (dist < 0.0001) {
            return
          }
        }
        
        const newPoints: [number, number][] = [...polygonPoints, newPoint]
        setPolygonPoints(newPoints)
        onPolygonDraw(newPoints)
      }
    },
  })

  if (geofence?.polygon) {
    const coords = geofence.polygon.coordinates[0].map((c: number[]) => [c[1], c[0]] as [number, number])
    return <Polygon positions={coords} color="blue" />
  }

  if (geofence?.center_lat && geofence?.center_lon && geofence?.radius_meters) {
    return (
      <Circle
        center={[parseFloat(geofence.center_lat), parseFloat(geofence.center_lon)]}
        radius={parseInt(geofence.radius_meters)}
        color="blue"
      />
    )
  }

  if (polygonPoints.length > 0) {
    return <Polygon positions={polygonPoints} color="blue" />
  }

  return null
}

export default function SiteDetail() {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const [site, setSite] = useState<Site | null>(null)
  const [geofences, setGeofences] = useState<Geofence[]>([])
  const [ipRules, setIpRules] = useState<IPRule[]>([])
  const [activeTab, setActiveTab] = useState<'filter' | 'geofence' | 'ip-rules'>('filter')
  const [loading, setLoading] = useState(true)
  const [userRole, setUserRole] = useState<string>('viewer')

  const [filterMode, setFilterMode] = useState<FilterMode>('disabled')
  const [newRule, setNewRule] = useState({ cidr: '', action: 'deny' })
  const [geofenceMode, setGeofenceMode] = useState<'polygon' | 'circle'>('circle')
  const [newGeofence, setNewGeofence] = useState({ center_lat: '', center_lon: '', radius_meters: '5000' })
  const [polygonCoords, setPolygonCoords] = useState<[number, number][]>([])
  const [saving, setSaving] = useState(false)
  const [mapCenter, setMapCenter] = useState<[number, number]>([51.505, -0.09])
  const [mapZoom, setMapZoom] = useState(13)
  const [showAddGeofence, setShowAddGeofence] = useState(false)
  const [selectedGeofence, setSelectedGeofence] = useState<Geofence | null>(null)

  useEffect(() => {
    if (siteId) loadData()
  }, [siteId])

  const loadData = async () => {
    try {
      const [siteRes, geoRes, rulesRes] = await Promise.all([
        sitesApi.get(siteId!),
        geofencesApi.list(siteId!),
        ipRulesApi.list(siteId!),
      ])
      setSite(siteRes.data)
      setFilterMode(siteRes.data.filter_mode)
      setUserRole(siteRes.data.my_role || 'viewer')
      setGeofences(geoRes.data)
      setIpRules(rulesRes.data)
      setPolygonCoords([])
      
      if (geoRes.data.length > 0) {
        const gf = geoRes.data[0]
        if (gf.polygon && gf.polygon.coordinates && gf.polygon.coordinates[0]) {
          setGeofenceMode('polygon')
          const coords = gf.polygon.coordinates[0]
          const lats = coords.map((c: number[]) => c[1])
          const lons = coords.map((c: number[]) => c[0])
          const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2
          const centerLon = (Math.min(...lons) + Math.max(...lons)) / 2
          setMapCenter([centerLat, centerLon])
          setMapZoom(13)
        } else if (gf.center_lat && gf.center_lon) {
          setGeofenceMode('circle')
          setMapCenter([parseFloat(gf.center_lat), parseFloat(gf.center_lon)])
          setMapZoom(13)
        }
      }
    } catch (error) {
      console.error('Failed to load site data:', error)
    } finally {
      setLoading(false)
    }
  }

  const updateFilterMode = async (mode: FilterMode) => {
    try {
      await sitesApi.updateFilter(siteId!, { filter_mode: mode })
      setFilterMode(mode)
    } catch (error) {
      console.error('Failed to update filter mode:', error)
    }
  }

  const addIPRule = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await ipRulesApi.create(siteId!, { ...newRule, priority: 0 })
      setNewRule({ cidr: '', action: 'deny' })
      loadData()
    } catch (error) {
      console.error('Failed to add IP rule:', error)
    }
  }

  const deleteIPRule = async (ruleId: string) => {
    try {
      await ipRulesApi.delete(siteId!, ruleId)
      loadData()
    } catch (error) {
      console.error('Failed to delete IP rule:', error)
    }
  }

  const addGeofence = async (e: React.FormEvent) => {
    e.preventDefault()
    if (saving) return
    
    console.log('Adding geofence:', geofenceMode, newGeofence, polygonCoords)
    setSaving(true)
    try {
      if (selectedGeofence) {
        if (geofenceMode === 'circle') {
          if (!newGeofence.center_lat || !newGeofence.center_lon) {
            alert('Please click on the map to set center location or enter coordinates')
            return
          }
          await geofencesApi.update(siteId!, selectedGeofence.id, {
            name: selectedGeofence.name || 'Main Geofence',
            center_lat: parseFloat(newGeofence.center_lat),
            center_lon: parseFloat(newGeofence.center_lon),
            radius_meters: parseInt(newGeofence.radius_meters),
          })
        } else if (geofenceMode === 'polygon') {
          if (polygonCoords.length < 3) {
            alert('Please draw at least 3 points on the map to create a polygon')
            return
          }
          const polygon = {
            type: 'Polygon',
            coordinates: [polygonCoords.map(p => [p[1], p[0]])]
          }
          await geofencesApi.update(siteId!, selectedGeofence.id, {
            name: selectedGeofence.name || 'Polygon Geofence',
            polygon: polygon,
          })
        }
      } else {
        if (geofenceMode === 'circle') {
          if (!newGeofence.center_lat || !newGeofence.center_lon) {
            alert('Please click on the map to set center location or enter coordinates')
            return
          }
          await geofencesApi.create(siteId!, {
            name: 'Main Geofence',
            center_lat: parseFloat(newGeofence.center_lat),
            center_lon: parseFloat(newGeofence.center_lon),
            radius_meters: parseInt(newGeofence.radius_meters),
          })
        } else if (geofenceMode === 'polygon') {
          if (polygonCoords.length < 3) {
            alert('Please draw at least 3 points on the map to create a polygon')
            return
          }
          const polygon = {
            type: 'Polygon',
            coordinates: [polygonCoords.map(p => [p[1], p[0]])]
          }
          await geofencesApi.create(siteId!, {
            name: 'Polygon Geofence',
            polygon: polygon,
          })
        }
      }
      setNewGeofence({ center_lat: '', center_lon: '', radius_meters: '5000' })
      setPolygonCoords([])
      setShowAddGeofence(false)
      setSelectedGeofence(null)
      await loadData()
      alert(selectedGeofence ? 'Geofence updated successfully!' : 'Geofence saved successfully!')
    } catch (error) {
      console.error('Failed to add geofence:', error)
      alert('Failed to save geofence: ' + (error as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="container">Loading...</div>
  }

  if (!site) {
    return <div className="container">Site not found</div>
  }

  return (
    <div>
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/sites')}>
            Back
          </button>
          <h1>{site.name}</h1>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Link to={`/sites/${siteId}/users`} className="btn btn-secondary">
            Users
          </Link>
          <Link to={`/sites/${siteId}/content`} className="btn btn-secondary">
            Content
          </Link>
          <Link to={`/sites/${siteId}/audit`} className="btn btn-secondary">
            Audit Logs
          </Link>
        </div>
      </header>

      <div className="container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'filter' ? 'active' : ''}`}
            onClick={() => setActiveTab('filter')}
          >
            Filter Settings
          </button>
          {(filterMode === 'geo' || filterMode === 'ip_and_geo') && (
            <button
              className={`tab ${activeTab === 'geofence' ? 'active' : ''}`}
              onClick={() => setActiveTab('geofence')}
            >
              Geofence
            </button>
          )}
          {(filterMode === 'ip' || filterMode === 'ip_and_geo') && (
            <button
              className={`tab ${activeTab === 'ip-rules' ? 'active' : ''}`}
              onClick={() => setActiveTab('ip-rules')}
            >
              IP Rules
            </button>
          )}
        </div>

        {activeTab === 'filter' && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Access Control Mode</h2>
            </div>
            <div className="form-group">
              <select
                className="form-select"
                value={filterMode}
                disabled={userRole === 'viewer' || userRole === 'editor'}
                onChange={(e) => updateFilterMode(e.target.value as FilterMode)}
              >
                <option value="disabled">Disabled - No filtering</option>
                <option value="ip">IP Only - Filter by IP address</option>
                <option value="geo">Geo Only - Filter by GPS coordinates</option>
                <option value="ip_and_geo">IP + Geo - Both required</option>
              </select>
            </div>
            {userRole === 'viewer' && (
              <p style={{ color: 'var(--gray-500)', fontSize: '14px', marginTop: '12px' }}>
                You have view-only access to this site.
              </p>
            )}
            {userRole === 'editor' && (
              <p style={{ color: 'var(--gray-500)', fontSize: '14px', marginTop: '12px' }}>
                You can view filters but cannot change the filter mode.
              </p>
            )}
          </div>
        )}

        {activeTab === 'geofence' && (filterMode === 'geo' || filterMode === 'ip_and_geo') && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Geofence Configuration</h2>
              <button 
                className="btn btn-primary" 
                disabled={userRole === 'viewer'}
                onClick={() => {
                  if (showAddGeofence) {
                    setShowAddGeofence(false)
                    setSelectedGeofence(null)
                    setNewGeofence({ center_lat: '', center_lon: '', radius_meters: '5000' })
                    setPolygonCoords([])
                  } else {
                    setShowAddGeofence(true)
                  }
                }}
              >
                {showAddGeofence ? 'Cancel' : '+ Add Geofence'}
              </button>
            </div>
            
            {geofences.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ marginBottom: '12px' }}>Active Geofences ({geofences.length})</h3>
                {geofences.map((gf, idx) => (
                  <div key={gf.id} style={{ marginBottom: '12px', padding: '12px', background: '#f0fdf4', borderRadius: '6px', border: '1px solid #bbf7d0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <strong>{gf.name || `Geofence ${idx + 1}`}</strong>
                        {gf.polygon ? (
                          <span> (Polygon)</span>
                        ) : (
                          <span> (Circle: {gf.radius_meters}m radius at {gf.center_lat}, {gf.center_lon})</span>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button 
                          className="btn btn-secondary" 
                          onClick={() => {
                            setSelectedGeofence(gf)
                            setShowAddGeofence(true)
                            if (gf.polygon) {
                              setGeofenceMode('polygon')
                              if (gf.polygon.coordinates && gf.polygon.coordinates[0]) {
                                const coords = gf.polygon.coordinates[0]
                                const lats = coords.map((c: number[]) => c[1])
                                const lons = coords.map((c: number[]) => c[0])
                                const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2
                                const centerLon = (Math.min(...lons) + Math.max(...lons)) / 2
                                setMapCenter([centerLat, centerLon])
                                setMapZoom(13)
                              }
                            } else {
                              setGeofenceMode('circle')
                              setNewGeofence({
                                center_lat: gf.center_lat || '',
                                center_lon: gf.center_lon || '',
                                radius_meters: gf.radius_meters || '5000'
                              })
                              if (gf.center_lat && gf.center_lon) {
                                setMapCenter([parseFloat(gf.center_lat), parseFloat(gf.center_lon)])
                                setMapZoom(13)
                              }
                            }
                          }}
                        >
                          Edit
                        </button>
                        <button 
                          className="btn btn-danger" 
                          onClick={async () => {
                            if (confirm('Delete this geofence?')) {
                              await geofencesApi.delete(siteId!, gf.id)
                              loadData()
                            }
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {geofences.length === 0 && !showAddGeofence && (
              <div style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>
                No geofences configured. Click "Add Geofence" to create one.
              </div>
            )}
            
            {showAddGeofence && (
              <>
            <div className="map-container" style={{ marginBottom: '20px' }}>
              <MapContainer key={geofences.map(g => g.id).join('-')} center={mapCenter} zoom={mapZoom} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {geofences.map(gf => (
                  gf.polygon ? (
                    <MapDrawer key={gf.id} geofence={gf} />
                  ) : (
                    <Circle
                      key={gf.id}
                      center={[parseFloat(gf.center_lat!), parseFloat(gf.center_lon!)]}
                      radius={parseInt(gf.radius_meters!)}
                      color="blue"
                    />
                  )
                ))}
                {geofenceMode === 'circle' && (
                  <MapDrawer 
                    geofence={null} 
                    onCenterClick={(lat, lon) => {
                      setNewGeofence({ ...newGeofence, center_lat: lat.toFixed(6), center_lon: lon.toFixed(6) })
                      setMapCenter([lat, lon])
                    }} 
                  />
                )}
                {geofenceMode === 'polygon' && (
                  <MapDrawer 
                    geofence={null} 
                    onPolygonDraw={(coords) => {
                      setPolygonCoords(coords)
                    }} 
                  />
                )}
              </MapContainer>
            </div>

            {geofenceMode === 'polygon' && !geofences[0] && (
              <div style={{ marginBottom: '16px', padding: '12px', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                <strong>Polygon Mode:</strong> Click on the map to draw points. 
                {polygonCoords.length > 0 && <span> You have {polygonCoords.length} points. Need at least 3.</span>}
                {!polygonCoords.length && <span> Click at least 3 points to create a polygon.</span>}
              </div>
            )}

            <form onSubmit={addGeofence}>
              <div className="form-group">
                <label className="form-label">Geofence Type</label>
                <select
                  className="form-select"
                  value={geofenceMode}
                  onChange={(e) => setGeofenceMode(e.target.value as 'polygon' | 'circle')}
                >
                  <option value="circle">Circle (Center + Radius)</option>
                  <option value="polygon">Polygon (Click on map to draw)</option>
                </select>
              </div>
              {geofenceMode === 'circle' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Center Latitude</label>
                    <input
                      type="number"
                      step="any"
                      className="form-input"
                      value={newGeofence.center_lat}
                      onChange={(e) => setNewGeofence({ ...newGeofence, center_lat: e.target.value })}
                      placeholder="51.505"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Center Longitude</label>
                    <input
                      type="number"
                      step="any"
                      className="form-input"
                      value={newGeofence.center_lon}
                      onChange={(e) => setNewGeofence({ ...newGeofence, center_lon: e.target.value })}
                      placeholder="-0.09"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Radius (meters)</label>
                    <input
                      type="number"
                      className="form-input"
                      value={newGeofence.radius_meters}
                      onChange={(e) => setNewGeofence({ ...newGeofence, radius_meters: e.target.value })}
                    />
                  </div>
                </>
              )}
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : selectedGeofence ? 'Update Geofence' : 'Save Geofence'}
              </button>
              {(polygonCoords.length > 0 || newGeofence.center_lat) && (
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  style={{ marginLeft: '8px' }}
                  onClick={() => {
                    setPolygonCoords([])
                    setNewGeofence({ center_lat: '', center_lon: '', radius_meters: '5000' })
                  }}
                >
                  Clear
                </button>
              )}
            </form>
              </>
            )}
          </div>
        )}

        {activeTab === 'ip-rules' && (filterMode === 'ip' || filterMode === 'ip_and_geo') && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">IP Rules</h2>
            </div>

            <form onSubmit={addIPRule} style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="CIDR (e.g., 192.168.1.0/24)"
                  value={newRule.cidr}
                  onChange={(e) => setNewRule({ ...newRule, cidr: e.target.value })}
                  required
                  disabled={userRole === 'viewer'}
                  style={{ flex: 2 }}
                />
                <select
                  className="form-select"
                  value={newRule.action}
                  onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                  disabled={userRole === 'viewer'}
                  style={{ flex: 1 }}
                >
                  <option value="allow">Allow</option>
                  <option value="deny">Deny</option>
                </select>
                <button type="submit" className="btn btn-primary" disabled={userRole === 'viewer'}>
                  Add Rule
                </button>
              </div>
            </form>

            {ipRules.length === 0 ? (
              <div className="empty-state">No IP rules configured</div>
            ) : (
              <div className="rule-list">
                {ipRules.map((rule) => (
                  <div key={rule.id} className="rule-item">
                    <span className="rule-cidr">{rule.cidr}</span>
                    <div className="rule-actions">
                      <span className={`badge ${rule.action === 'allow' ? 'badge-success' : 'badge-danger'}`}>
                        {rule.action}
                      </span>
                      <button className="btn btn-danger" onClick={() => deleteIPRule(rule.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
