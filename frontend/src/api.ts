import type { Analysis, Capabilities, Job, OutputFormat } from './types'

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string }
    return payload.detail ?? `Erreur HTTP ${response.status}`
  } catch {
    return `Le serveur a répondu avec l’erreur ${response.status}.`
  }
}

export async function getCapabilities(): Promise<Capabilities> {
  const response = await fetch(`${API_BASE}/api/capabilities`)
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<Capabilities>
}

export function uploadFile(
  file: File,
  outputFormat: OutputFormat,
  onProgress: (progress: number) => void,
): Promise<{ job_id: string }> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${API_BASE}/api/jobs/upload`)
    request.responseType = 'json'
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) resolve(request.response as { job_id: string })
      else reject(new Error(request.response?.detail ?? `Erreur HTTP ${request.status}`))
    }
    request.onerror = () => reject(new Error('Impossible de joindre le serveur.'))
    const form = new FormData()
    form.append('file', file)
    form.append('output_format', outputFormat)
    request.send(form)
  })
}

export async function submitYoutube(
  url: string,
  outputFormat: OutputFormat,
): Promise<{ job_id: string }> {
  const response = await fetch(`${API_BASE}/api/jobs/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, output_format: outputFormat, rights_confirmed: true }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<{ job_id: string }>
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`)
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<Job>
}

export async function deleteJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: 'DELETE' })
}

export function downloadUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/download`
}

export function uploadAnalysis(
  file: File,
  onProgress: (progress: number) => void,
): Promise<{ analysis_id: string }> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${API_BASE}/api/analysis/upload`)
    request.responseType = 'json'
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(request.response as { analysis_id: string })
      } else reject(new Error(request.response?.detail ?? `Erreur HTTP ${request.status}`))
    }
    request.onerror = () => reject(new Error('Impossible de joindre le serveur.'))
    const form = new FormData()
    form.append('file', file)
    request.send(form)
  })
}

export async function submitYoutubeAnalysis(url: string): Promise<{ analysis_id: string }> {
  const response = await fetch(`${API_BASE}/api/analysis/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, rights_confirmed: true }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<{ analysis_id: string }>
}

export async function getAnalysis(analysisId: string): Promise<Analysis> {
  const response = await fetch(`${API_BASE}/api/analysis/${analysisId}`)
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<Analysis>
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  await fetch(`${API_BASE}/api/analysis/${analysisId}`, { method: 'DELETE' })
}
