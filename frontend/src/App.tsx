import { useEffect, useMemo, useRef, useState } from 'react'
import { deleteJob, downloadUrl, getCapabilities, getJob, submitYoutube, uploadFile } from './api'
import { strings } from './strings'
import type { Capabilities, Job, OutputFormat } from './types'
import './styles.css'

const ALLOWED_EXTENSIONS = ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg']

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

function App() {
  const [mode, setMode] = useState<'file' | 'youtube'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [rights, setRights] = useState(false)
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('mp3')
  const [job, setJob] = useState<Job | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const localPreview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => { if (localPreview) URL.revokeObjectURL(localPreview) }, [localPreview])

  useEffect(() => {
    getCapabilities().then(setCapabilities).catch(() => setError('Le serveur de conversion est inaccessible.'))
  }, [])

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    const poll = async () => {
      try {
        const next = await getJob(jobId)
        if (cancelled) return
        setJob(next)
        if (next.status === 'queued' || next.status === 'processing') window.setTimeout(poll, 800)
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Le suivi du traitement a échoué.')
      }
    }
    void poll()
    return () => { cancelled = true }
  }, [jobId])

  const working = Boolean(jobId && (!job || job.status === 'queued' || job.status === 'processing'))
  const canSubmit = mode === 'file' ? Boolean(file) : Boolean(url.trim() && rights && capabilities?.youtube_available)

  const chooseFile = (selected?: File) => {
    if (!selected) return
    const extension = selected.name.split('.').pop()?.toLowerCase() ?? ''
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setFile(null)
      setError(`Format non accepté. Choisissez ${ALLOWED_EXTENSIONS.join(', ')}.`)
      return
    }
    if (capabilities && selected.size > capabilities.max_upload_mb * 1024 * 1024) {
      setFile(null)
      setError(`Ce fichier dépasse la limite de ${capabilities.max_upload_mb} Mo.`)
      return
    }
    setError(null)
    setFile(selected)
  }

  const convert = async () => {
    if (!canSubmit || working) return
    setError(null)
    setJob(null)
    try {
      let created: { job_id: string }
      if (mode === 'file' && file) {
        setUploadProgress(0)
        created = await uploadFile(file, outputFormat, setUploadProgress)
        setUploadProgress(null)
      } else {
        created = await submitYoutube(url.trim(), outputFormat)
      }
      setJobId(created.job_id)
    } catch (caught) {
      setUploadProgress(null)
      setError(caught instanceof Error ? caught.message : 'La conversion n’a pas pu démarrer.')
    }
  }

  const reset = async () => {
    const previousId = jobId
    setJobId(null)
    setJob(null)
    setFile(null)
    setUrl('')
    setRights(false)
    setError(null)
    setUploadProgress(null)
    if (previousId) await deleteJob(previousId).catch(() => undefined)
  }

  const visibleProgress = uploadProgress ?? job?.progress ?? 0
  const visibleStage = uploadProgress !== null ? strings.stages.upload : job ? strings.stages[job.stage] : ''
  const serviceUnavailable = capabilities && !capabilities.rubberband_available

  return (
    <main className="page-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <section className="app-card" aria-labelledby="page-title">
        <header className="hero">
          <div className="mark" aria-hidden="true"><span>432</span><small>Hz</small></div>
          <p className="eyebrow">PITCH CONVERTER</p>
          <h1 id="page-title">Convertisseur musical <em>432 Hz</em></h1>
          <p className="intro">Décalez la hauteur de votre morceau de 440 vers 432 Hz, tout en conservant son tempo et sa durée.</p>
        </header>

        {serviceUnavailable && <div className="alert error" role="alert">Le serveur ne possède pas le filtre Rubber Band requis. La conversion est désactivée.</div>}
        {error && <div className="alert error" role="alert">{error}</div>}
        {job?.status === 'failed' && <div className="alert error" role="alert">{job.error ?? 'La conversion a échoué.'}</div>}

        {!jobId && (
          <>
            <div className="tabs" role="tablist" aria-label="Source du morceau">
              <button role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'active' : ''} onClick={() => setMode('file')}>Fichier audio</button>
              <button role="tab" aria-selected={mode === 'youtube'} className={mode === 'youtube' ? 'active' : ''} onClick={() => setMode('youtube')}>Lien YouTube</button>
            </div>

            {mode === 'file' ? (
              <div key="file-mode">
                <button
                  type="button"
                  className={`drop-zone ${file ? 'has-file' : ''}`}
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files[0]) }}
                >
                  <span className="upload-icon" aria-hidden="true">↥</span>
                  {file ? <><strong>{file.name}</strong><span>{formatBytes(file.size)} · Cliquer pour remplacer</span></> : <><strong>Déposez votre morceau ici</strong><span>ou touchez pour parcourir vos fichiers</span></>}
                </button>
                <input ref={inputRef} className="sr-only" type="file" accept=".mp3,.wav,.flac,.m4a,.aac,.ogg,audio/*" onChange={(event) => chooseFile(event.target.files?.[0])} />
                <p className="formats-note">MP3, WAV, FLAC, M4A, AAC ou OGG{capabilities ? ` · ${capabilities.max_upload_mb} Mo maximum` : ''}</p>
                {localPreview && <div className="preview"><span>Original</span><audio controls src={localPreview}>Votre navigateur ne peut pas lire ce fichier.</audio></div>}
              </div>
            ) : (
              <div key="youtube-mode" className="youtube-panel">
                <label htmlFor="youtube-url">Adresse de la vidéo YouTube</label>
                <input id="youtube-url" type="url" inputMode="url" placeholder="https://youtu.be/…" value={url} onChange={(event) => setUrl(event.target.value)} />
                {capabilities && !capabilities.youtube_available && <p className="inline-warning">L’import YouTube est indisponible sur ce serveur. L’import de fichier reste actif.</p>}
                <label className="rights-check"><input type="checkbox" checked={rights} onChange={(event) => setRights(event.target.checked)} /><span>Je confirme disposer des droits ou de l’autorisation nécessaires pour télécharger et transformer ce contenu.</span></label>
              </div>
            )}

            <fieldset className="output-options">
              <legend>Format du résultat</legend>
              <div className="format-grid">
                {(Object.keys(strings.formats) as OutputFormat[]).map((format) => (
                  <label key={format} className={outputFormat === format ? 'selected' : ''}>
                    <input type="radio" name="format" value={format} checked={outputFormat === format} onChange={() => setOutputFormat(format)} />
                    <strong>{strings.formats[format].title}</strong><span>{strings.formats[format].detail}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <button className="primary-button" disabled={!canSubmit || Boolean(serviceUnavailable)} onClick={() => void convert()}><span>Convertir en 432 Hz</span><span aria-hidden="true">→</span></button>
          </>
        )}

        {jobId && job?.status !== 'completed' && (
          <section className="progress-panel" aria-live="polite">
            <div className="vinyl" aria-hidden="true"><div /></div>
            <p className="stage">{visibleStage || 'Mise en file d’attente'}</p>
            <p className="progress-value">{visibleProgress}<small>%</small></p>
            <progress max="100" value={visibleProgress}>{visibleProgress}%</progress>
            <p className="patience">Gardez cette page ouverte pendant le traitement.</p>
            {job?.status === 'failed' && <button className="secondary-button" onClick={() => void reset()}>Réessayer avec un autre morceau</button>}
          </section>
        )}

        {job?.status === 'completed' && (
          <section className="result-panel" aria-live="polite">
            <div className="success-icon" aria-hidden="true">✓</div>
            <p className="eyebrow">CONVERSION TERMINÉE</p>
            <h2>Votre morceau est prêt</h2>
            <p>Hauteur déplacée de −31,77 cents, durée et tempo préservés.</p>
            <div className="preview result"><span>Résultat 432 Hz</span><audio controls src={downloadUrl(job.job_id)}>Votre navigateur ne peut pas lire ce fichier.</audio></div>
            <a className="primary-button" href={downloadUrl(job.job_id)} download={job.download_name ?? undefined}><span>Télécharger le fichier</span><span aria-hidden="true">↓</span></a>
            <button className="text-button" onClick={() => void reset()}>Convertir un autre morceau</button>
            {job.expires_at && <small className="expiry">Téléchargement disponible temporairement.</small>}
          </section>
        )}

        <footer><span>440 → 432</span><p>Le réglage applique un décalage relatif. Il ne détecte pas l’accordage d’origine.</p></footer>
      </section>
    </main>
  )
}

export default App
