export type OutputFormat = 'mp3' | 'wav' | 'flac'
export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed'
export type JobStage = 'upload' | 'download' | 'preparation' | 'conversion' | 'finalization' | 'ready'

export interface Job {
  job_id: string
  status: JobStatus
  progress: number
  stage: JobStage
  error: string | null
  expires_at: string | null
  download_name: string | null
}

export interface Capabilities {
  input_formats: string[]
  output_formats: OutputFormat[]
  max_upload_mb: number
  max_duration_seconds: number
  youtube_available: boolean
  rubberband_available: boolean
  tuning_analysis_available?: boolean
}

export interface TuningResult {
  estimated_reference_hz: number
  offset_from_440_cents: number
  offset_from_432_cents: number
  classification: '432' | '440' | 'other' | 'uncertain'
  confidence: number
  analyzed_seconds: number
  diagnostic: string
  explanation: string
}

export interface Analysis {
  analysis_id: string
  status: JobStatus
  progress: number
  stage: 'download' | 'preparation' | 'analysis' | 'ready'
  error: string | null
  result: TuningResult | null
  expires_at: string | null
}
