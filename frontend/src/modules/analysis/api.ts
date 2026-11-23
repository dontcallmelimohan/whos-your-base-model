import { api, buildQuery } from '@/shared/api'
import type { AnalysisResponse } from '@/shared/types'

export const fetchAnalysis = (snapshotId?: string) =>
  api<AnalysisResponse>(`/api/analysis${buildQuery({ snapshot_id: snapshotId })}`)
