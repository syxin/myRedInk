/**
 * 认证工具模块
 *
 * 管理 token 的存取，提供 axios 拦截器和 fetch header 注入。
 */

const TOKEN_KEY = 'redink_auth_token'

/** 获取当前 token */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/** 保存 token */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 清除 token */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** 是否已登录（有 token） */
export function isAuthenticated(): boolean {
  return !!getToken()
}

/** 登录 */
export async function login(password: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  const data = await response.json()
  if (data.success && data.token) {
    setToken(data.token)
    return { success: true }
  }
  return { success: false, error: data.error || '登录失败' }
}

/** 检查 token 是否有效 */
export async function checkAuth(): Promise<{ valid: boolean; auth_enabled: boolean }> {
  try {
    const response = await fetch('/api/auth/check', {
      headers: getAuthHeaders(),
    })
    const data = await response.json()
    return { valid: data.valid, auth_enabled: data.auth_enabled }
  } catch {
    return { valid: false, auth_enabled: false }
  }
}

/** 检查认证功能是否启用 */
export async function getAuthStatus(): Promise<boolean> {
  try {
    const response = await fetch('/api/auth/status')
    const data = await response.json()
    return data.auth_enabled === true
  } catch {
    return false
  }
}

/** 返回带 Authorization header 的 headers 对象（用于 fetch） */
export function getAuthHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  const token = getToken()
  if (token) {
    headers['Authorization'] = Bearer 
  }
  return headers
}
