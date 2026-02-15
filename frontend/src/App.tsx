import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Login from './pages/Login'
import Sites from './pages/Sites'
import SiteDetail from './pages/SiteDetail'
import AuditLogs from './pages/AuditLogs'
import SiteUsers from './pages/SiteUsers'
import SiteContent from './pages/SiteContent'
import Users from './pages/Users'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <Users />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sites"
          element={
            <ProtectedRoute>
              <Sites />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sites/:siteId"
          element={
            <ProtectedRoute>
              <SiteDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sites/:siteId/audit"
          element={
            <ProtectedRoute>
              <AuditLogs />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sites/:siteId/users"
          element={
            <ProtectedRoute>
              <SiteUsers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sites/:siteId/content"
          element={
            <ProtectedRoute>
              <SiteContent />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/sites" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
