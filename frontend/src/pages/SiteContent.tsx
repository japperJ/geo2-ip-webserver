import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sitesApi, contentApi } from '../services/api'

interface ContentFile {
  key: string
  filename: string
  content_type: string
  size: number
  uploaded_at: string
}

export default function SiteContent() {
  const { siteId } = useParams<{ siteId: string }>()
  const navigate = useNavigate()
  const [files, setFiles] = useState<ContentFile[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [site, setSite] = useState<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (siteId) loadData()
  }, [siteId])

  const loadData = async () => {
    try {
      const [siteRes, filesRes] = await Promise.all([
        sitesApi.get(siteId!),
        contentApi.list(siteId!),
      ])
      setSite(siteRes.data)
      setFiles(filesRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      await contentApi.upload(siteId!, file)
      await loadData()
      alert('File uploaded successfully!')
    } catch (error) {
      console.error('Failed to upload:', error)
      alert('Failed to upload file')
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const deleteFile = async (key: string) => {
    if (!confirm('Delete this file?')) return
    try {
      await contentApi.delete(siteId!, key)
      await loadData()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) return '🖼️'
    if (contentType.includes('html')) return '📄'
    if (contentType.includes('css')) return '🎨'
    if (contentType.includes('javascript')) return '⚡'
    return '📁'
  }

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
          <h1>Content - {site?.name}</h1>
        </div>
        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleUpload}
            style={{ display: 'none' }}
            id="file-upload"
          />
          <label htmlFor="file-upload" className="btn btn-primary" style={{ cursor: 'pointer' }}>
            {uploading ? 'Uploading...' : '+ Upload File'}
          </label>
        </div>
      </header>

      <div className="container">
        <div className="card" style={{ marginBottom: '20px', padding: '16px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
          <h3 style={{ marginBottom: '8px' }}>How to use</h3>
          <p style={{ margin: 0, color: '#666' }}>
            Upload HTML, CSS, JS, images, or other files. Access them at:<br />
            <code style={{ background: '#fff', padding: '4px 8px', borderRadius: '4px' }}>
              /s/{site?.hostname || '[hostname]'}/content/[filename]
            </code>
          </p>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Files ({files.length})</h2>
          </div>
          
          {files.length === 0 ? (
            <div className="empty-state">
              No files uploaded yet. Click "Upload File" to add content.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px', padding: '16px' }}>
              {files.map(file => (
                <div key={file.key} style={{ 
                  border: '1px solid #e5e7eb', 
                  borderRadius: '8px', 
                  padding: '16px',
                  background: '#fff'
                }}>
                  <div style={{ fontSize: '32px', textAlign: 'center', marginBottom: '8px' }}>
                    {getFileIcon(file.content_type)}
                  </div>
                  <div style={{ fontWeight: '500', marginBottom: '4px', wordBreak: 'break-all' }}>
                    {file.filename}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                    {formatSize(file.size)} • {file.content_type}
                  </div>
                  <div style={{ fontSize: '11px', color: '#999', marginBottom: '12px' }}>
                    {new Date(file.uploaded_at).toLocaleString()}
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      className="btn btn-danger"
                      style={{ flex: 1 }}
                      onClick={() => deleteFile(file.key)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
