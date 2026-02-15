import axios from 'axios'
import { useAuthStore } from '../store/auth'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const refreshToken = useAuthStore.getState().refreshToken
      if (refreshToken) {
        try {
          const response = await axios.post(
            `/api/auth/refresh`,
            null,
            { headers: { Authorization: `Bearer ${refreshToken}` } }
          )
          
          const { access_token, refresh_token } = response.data
          useAuthStore.getState().setToken(access_token, refresh_token)
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
          useAuthStore.getState().logout()
        }
      }
    }
    
    return Promise.reject(error)
  }
)

export const sitesApi = {
  list: () => api.get('/api/admin/sites'),
  get: (id: string) => api.get(`/api/admin/sites/${id}`),
  create: (data: { name: string; hostname?: string; path_prefix?: string }) =>
    api.post('/api/admin/sites', data),
  update: (id: string, data: any) => api.put(`/api/admin/sites/${id}`, data),
  delete: (id: string) => api.delete(`/api/admin/sites/${id}`),
  updateFilter: (id: string, data: any) => api.put(`/api/admin/sites/${id}/filter`, data),
}

export const geofencesApi = {
  list: (siteId: string) => api.get(`/api/admin/sites/${siteId}/geofences`),
  create: (siteId: string, data: any) =>
    api.post(`/api/admin/sites/${siteId}/geofences`, data),
  update: (siteId: string, geofenceId: string, data: any) =>
    api.put(`/api/admin/sites/${siteId}/geofences/${geofenceId}`, data),
  delete: (siteId: string, geofenceId: string) =>
    api.delete(`/api/admin/sites/${siteId}/geofences/${geofenceId}`),
}

export const ipRulesApi = {
  list: (siteId: string) => api.get(`/api/admin/sites/${siteId}/ip-rules`),
  create: (siteId: string, data: any) =>
    api.post(`/api/admin/sites/${siteId}/ip-rules`, data),
  update: (siteId: string, ruleId: string, data: any) =>
    api.put(`/api/admin/sites/${siteId}/ip-rules/${ruleId}`, data),
  delete: (siteId: string, ruleId: string) =>
    api.delete(`/api/admin/sites/${siteId}/ip-rules/${ruleId}`),
}

export const auditApi = {
  list: (siteId: string, params?: any) =>
    api.get(`/api/admin/sites/${siteId}/audit`, { params }),
  export: (siteId: string, params?: any) =>
    api.get(`/api/admin/sites/${siteId}/audit/export`, { params }),
}

export const usersApi = {
  list: (search?: string) => 
    api.get('/api/auth/users', { params: { search } }),
}

export const siteUsersApi = {
  list: (siteId: string) => api.get(`/api/admin/sites/${siteId}/users`),
  add: (siteId: string, data: { user_id: string; role: string }) =>
    api.post(`/api/admin/sites/${siteId}/users`, data),
  updateRole: (siteId: string, siteUserId: string, role: string) =>
    api.put(`/api/admin/sites/${siteId}/users/${siteUserId}?role=${role}`),
  delete: (siteId: string, siteUserId: string) =>
    api.delete(`/api/admin/sites/${siteId}/users/${siteUserId}`),
}

export const contentApi = {
  list: (siteId: string) => api.get(`/api/admin/sites/${siteId}/content`),
  upload: (siteId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/api/admin/sites/${siteId}/content/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete: (siteId: string, key: string) =>
    api.delete(`/api/admin/sites/${siteId}/content/${key}`),
}

export const authApi = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post('/api/auth/register', data),
  createUser: (data: { email: string; username: string; password: string; full_name?: string }) => {
    const payload = { ...data }
    if (!payload.full_name) delete payload.full_name
    return api.post('/api/auth/users', payload)
  },
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/api/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
}
