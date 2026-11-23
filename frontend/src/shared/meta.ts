import { api } from '@/shared/api'
import type { Meta } from '@/shared/types'

let cached: Meta | null = null

export async function fetchMeta(): Promise<Meta> {
  if (!cached) cached = await api<Meta>('/api/meta')
  return cached
}
