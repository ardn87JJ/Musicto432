import type { Analysis, Capabilities, Job, OutputFormat, YouTubeMetadata } from './types'

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
  sourceReferenceHz: number,
  targetReferenceHz: number,
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
    form.append('source_reference_hz', String(sourceReferenceHz))
    form.append('target_reference_hz', String(targetReferenceHz))
    request.send(form)
  })
}

export async function submitYoutube(
  url: string,
  outputFormat: OutputFormat,
  sourceReferenceHz: number,
  targetReferenceHz: number,
  title?: string,
): Promise<{ job_id: string }> {
  const response = await fetch(`${API_BASE}/api/jobs/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url,
      output_format: outputFormat,
      source_reference_hz: sourceReferenceHz,
      target_reference_hz: targetReferenceHz,
      title,
      rights_confirmed: true,
    }),
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

export async function inspectYoutube(url: string): Promise<YouTubeMetadata> {
  const response = await fetch(`${API_BASE}/api/youtube/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, rights_confirmed: true }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<YouTubeMetadata>
}

export async function downloadBatch(jobIds: string[]): Promise<void> {
  const response = await fetch(`${API_BASE}/api/jobs/batch-download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds }),
  })
  if (!response.ok) throw new Error(await readError(response))
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'MusicTo432_resultats.zip'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
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
