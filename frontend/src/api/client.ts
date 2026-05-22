import axios from 'axios'

const TOKEN_KEY = 'ps_token'

const axiosInstance = axios.create({
  baseURL: '',
})

axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Types
export interface User {
  id: string
  email: string
  plan: string
  is_active: boolean
  created_at: string
}

export interface Target {
  id: string
  domain: string
  verified: boolean
  verification_method: string
  verification_token: string
  verified_at: string | null
  created_at: string
}

export interface Scan {
  id: string
  target: string
  target_id: string
  status: string
  scope: string
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface Finding {
  id: string
  title: string
  description: string
  severity: string
  cvss_score: number | null
  affected_component: string
  proof: string | null
  fix_suggestion: string | null
  nis2_control: string | null
  source: string
  created_at: string
}

export interface Report {
  id: string
  scan_id: string
  status: string
  ai_summary: Record<string, unknown> | null
  nis2_gap_analysis: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export const api = {
  auth: {
    login: async (email: string, password: string) => {
      const res = await axiosInstance.post<{ access_token: string; token_type: string }>(
        '/auth/login',
        { email, password }
      )
      return res.data
    },
    register: async (email: string, password: string) => {
      const res = await axiosInstance.post<{ access_token: string; token_type: string }>(
        '/auth/register',
        { email, password }
      )
      return res.data
    },
    me: async () => {
      const res = await axiosInstance.get<User>('/auth/me')
      return res.data
    },
  },

  targets: {
    list: async () => {
      const res = await axiosInstance.get<Target[]>('/targets')
      return res.data
    },
    create: async (domain: string, verification_method: string) => {
      const res = await axiosInstance.post<Target>('/targets', { domain, verification_method })
      return res.data
    },
    verify: async (id: string) => {
      const res = await axiosInstance.post<{ verified: boolean; detail: string }>(
        `/targets/${id}/verify`
      )
      return res.data
    },
    delete: async (id: string) => {
      await axiosInstance.delete(`/targets/${id}`)
    },
  },

  scans: {
    list: async () => {
      const res = await axiosInstance.get<Scan[]>('/scans')
      return res.data
    },
    create: async (target_id: string, scope: string) => {
      const res = await axiosInstance.post<Scan>('/scans', { target_id, scope })
      return res.data
    },
    get: async (id: string) => {
      const res = await axiosInstance.get<Scan>(`/scans/${id}`)
      return res.data
    },
    getFindings: async (scan_id: string, severity?: string) => {
      const params: Record<string, string> = {}
      if (severity) params.severity = severity
      const res = await axiosInstance.get<Finding[]>(`/scans/${scan_id}/findings`, { params })
      return res.data
    },
  },

  reports: {
    trigger: async (scan_id: string) => {
      const res = await axiosInstance.post<Report>(`/reports/scans/${scan_id}`)
      return res.data
    },
    get: async (scan_id: string) => {
      const res = await axiosInstance.get<Report>(`/reports/scans/${scan_id}`)
      return res.data
    },
  },
}

export { TOKEN_KEY }
export default axiosInstance
