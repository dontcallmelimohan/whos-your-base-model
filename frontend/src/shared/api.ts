/**
 * 统一请求客户端。
 *
 * 约定：后端失败一律返回 {"error": {"code", "message", "detail"}}，
 * 这里统一抛 ApiError，页面只按 code 分支，不匹配中文文案。
 */

export class ApiError extends Error {
  code: string
  status: number
  detail: unknown

  constructor(code: string, message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.detail = detail
  }
}

export function buildQuery(params: object = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  if (!response.ok) {
    let code = 'http_error'
    let message = `请求失败（${response.status}）`
    let detail: unknown
    try {
      const body = await response.json()
      code = body?.error?.code ?? code
      message = body?.error?.message ?? message
      detail = body?.error?.detail
    } catch {
      /* 非 JSON 响应，保留默认文案 */
    }
    throw new ApiError(code, message, response.status, detail)
  }

  return (await response.json()) as T
}

export function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.message}（${error.code}）`
  return error instanceof Error ? error.message : String(error)
}
