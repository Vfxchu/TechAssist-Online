import axios from 'axios'

const API = axios.create({ 
  baseURL: import.meta.env.VITE_API_URL || '/api/v1' 
})

API.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred'
    console.error('[API Error]', error.config?.url, message)
    return Promise.reject(new Error(message))
  }
)

export const createTicket = (title, userId = 'user') =>
  API.post('/tickets', { title, user_id: userId }).then(r => r.data)

export const getTickets = (status = null) =>
  API.get('/tickets', { params: status ? { status } : {} }).then(r => r.data)

export const getTicket = (id) =>
  API.get(`/tickets/${id}`).then(r => r.data)

export const updateTicket = (id, data) =>
  API.patch(`/tickets/${id}`, data).then(r => r.data)

export const sendMessage = (ticketId, content, screenshotPath = null) =>
  API.post(`/tickets/${ticketId}/messages`, {
    content,
    screenshot_path: screenshotPath,
  }).then(r => r.data)

export const uploadScreenshot = (ticketId, file) => {
  const form = new FormData()
  form.append('file', file)
  return API.post(`/tickets/${ticketId}/screenshots`, form).then(r => r.data)
}

export const resolveTicket = (id) =>
  API.post(`/tickets/${id}/resolve`).then(r => r.data)

export const escalateTicket = (id) =>
  API.post(`/tickets/${id}/escalate`).then(r => r.data)

export const submitSatisfaction = (id, rating) =>
  API.post(`/tickets/${id}/satisfaction`, { rating }).then(r => r.data)

export const getAnalyticsSummary = () =>
  API.get('/analytics/summary').then(r => r.data)

export const getCommonIssues = () =>
  API.get('/analytics/common-issues').then(r => r.data)

export const searchSolutions = (q) =>
  API.get('/solutions/search', { params: { q } }).then(r => r.data)
