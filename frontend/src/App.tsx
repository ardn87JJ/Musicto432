import { useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteAnalysis,
  deleteJob,
  downloadBatch,
  downloadUrl,
  getAnalysis,
  getCapabilities,
  getJob,
  inspectYoutube,
  submitYoutube,
  submitYoutubeAnalysis,
  uploadAnalysis,
  uploadFile,
} from './api'
import { strings } from './strings'
import type { Analysis, Capabilities, Job, OutputFormat, YouTubeMetadata } from './types'
import './styles.css'

const ALLOWED_EXTENSIONS = ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg']
const BASE_URL = import.meta.env.BASE_URL

interface BatchItem {
  name: string
  status: 'waiting' | 'uploading' | 'processing' | 'completed' | 'failed' | 'stopped'
  progress: number
  jobId?: string
  downloadName?: string | null
  error?: string | null
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return 'Durée inconnue'
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${Math.round(seconds % 60).toString().padStart(2, '0')}`
}

function App() {
  const [feature, setFeature] = useState<'convert' | 'analyze'>(() => (
    new URLSearchParams(window.location.search).get('mode') === 'analyze' ? 'analyze' : 'convert'
  ))
  const [mode, setMode] = useState<'file' | 'youtube'>('file')
  const [files, setFiles] = useState<File[]>([])
  const [url, setUrl] = useState('')
  const [rights, setRights] = useState(false)
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('mp3')
  const [sourceReferenceHz, setSourceReferenceHz] = useState(440)
  const [targetReferenceHz, setTargetReferenceHz] = useState(432)
  const [job, setJob] = useState<Job | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [batchItems, setBatchItems] = useState<BatchItem[]>([])
  const [batchRunning, setBatchRunning] = useState(false)
  const [youtubeMetadata, setYoutubeMetadata] = useState<YouTubeMetadata | null>(null)
  const [youtubeInspecting, setYoutubeInspecting] = useState(false)
  const [online, setOnline] = useState(navigator.onLine)
  const inputRef = useRef<HTMLInputElement>(null)
  const batchRunningRef = useRef(false)
  const batchCancelledRef = useRef(false)
  const batchCurrentIdRef = useRef<string | null>(null)
  const file = files[0] ?? null

  const localPreview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => { if (localPreview) URL.revokeObjectURL(localPreview) }, [localPreview])

  useEffect(() => {
    getCapabilities().then(setCapabilities).catch(() => setError('Le serveur de conversion est inaccessible.'))
  }, [])

  useEffect(() => {
    const handleOnline = () => setOnline(true)
    const handleOffline = () => setOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (!jobId || batchRunningRef.current) return
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

  useEffect(() => {
    if (!analysisId) return
    let cancelled = false
    const poll = async () => {
      try {
        const next = await getAnalysis(analysisId)
        if (cancelled) return
        setAnalysis(next)
        if (next.status === 'queued' || next.status === 'processing') window.setTimeout(poll, 800)
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Le suivi de l’analyse a échoué.')
      }
    }
    void poll()
    return () => { cancelled = true }
  }, [analysisId])

  const working = Boolean(jobId && (!job || job.status === 'queued' || job.status === 'processing'))
  const analyzing = Boolean(analysisId && (!analysis || analysis.status === 'queued' || analysis.status === 'processing'))
  const validFrequencyChange = sourceReferenceHz >= 400 && sourceReferenceHz <= 480
    && targetReferenceHz >= 400 && targetReferenceHz <= 480
    && Math.abs(sourceReferenceHz - targetReferenceHz) >= 0.001
  const canSubmitSource = mode === 'file' ? files.length > 0 : Boolean(url.trim() && rights && capabilities?.youtube_available)
  const canSubmit = canSubmitSource && (feature === 'analyze' || validFrequencyChange)

  const chooseFiles = (selected: File[]) => {
    if (!selected.length) return
    for (const candidate of selected) {
      const extension = candidate.name.split('.').pop()?.toLowerCase() ?? ''
      if (!ALLOWED_EXTENSIONS.includes(extension)) {
        setFiles([])
        setError(`Le fichier « ${candidate.name} » n’est pas accepté. Choisissez ${ALLOWED_EXTENSIONS.join(', ')}.`)
        return
      }
      if (capabilities && candidate.size > capabilities.max_upload_mb * 1024 * 1024) {
        setFiles([])
        setError(`Le fichier « ${candidate.name} » dépasse la limite de ${capabilities.max_upload_mb} Mo.`)
        return
      }
    }
    setError(null)
    setNotice(null)
    setFiles(selected)
  }

  const chooseFile = (selected?: File) => { if (selected) chooseFiles([selected]) }

  const updateBatchItem = (index: number, changes: Partial<BatchItem>) => {
    setBatchItems((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...changes } : item
    )))
  }

  const runBatch = async () => {
    batchRunningRef.current = true
    setBatchRunning(true)
    batchCancelledRef.current = false
    setBatchItems(files.map((candidate) => ({ name: candidate.name, status: 'waiting', progress: 0 })))
    for (let index = 0; index < files.length; index += 1) {
      if (batchCancelledRef.current) break
      const candidate = files[index]
      try {
        updateBatchItem(index, { status: 'uploading', progress: 0 })
        const created = await uploadFile(
          candidate,
          outputFormat,
          sourceReferenceHz,
          targetReferenceHz,
          (progress) => {
          updateBatchItem(index, { progress: Math.round(progress * 0.1) })
          },
        )
        batchCurrentIdRef.current = created.job_id
        setJobId(created.job_id)
        updateBatchItem(index, { status: 'processing', jobId: created.job_id, progress: 10 })
        while (!batchCancelledRef.current) {
          const currentJob = await getJob(created.job_id)
          setJob(currentJob)
          updateBatchItem(index, { progress: 10 + Math.round(currentJob.progress * 0.9) })
          if (currentJob.status === 'completed') {
            updateBatchItem(index, {
              status: 'completed',
              progress: 100,
              downloadName: currentJob.download_name,
            })
            break
          }
          if (currentJob.status === 'failed') {
            updateBatchItem(index, { status: 'failed', error: currentJob.error })
            break
          }
          await new Promise((resolve) => window.setTimeout(resolve, 800))
        }
      } catch (caught) {
        if (!batchCancelledRef.current) {
          updateBatchItem(index, {
            status: 'failed',
            error: caught instanceof Error ? caught.message : 'Échec du traitement.',
          })
        }
      }
      batchCurrentIdRef.current = null
    }
    if (batchCancelledRef.current) {
      setBatchItems((current) => current.map((item) => (
        item.status === 'waiting' || item.status === 'processing' || item.status === 'uploading'
          ? { ...item, status: 'stopped' }
          : item
      )))
      setNotice('Traitement de la file arrêté.')
    } else {
      setNotice('Tous les fichiers de la file ont été traités.')
    }
    batchRunningRef.current = false
    setBatchRunning(false)
    setJobId(null)
    setJob(null)
  }

  const convert = async () => {
    if (!canSubmit || working) return
    setError(null)
    setNotice(null)
    setJob(null)
    if (mode === 'file' && files.length > 1) {
      await runBatch()
      return
    }
    try {
      let created: { job_id: string }
      if (mode === 'file' && file) {
        setUploadProgress(0)
        created = await uploadFile(
          file,
          outputFormat,
          sourceReferenceHz,
          targetReferenceHz,
          setUploadProgress,
        )
        setUploadProgress(null)
      } else {
        created = await submitYoutube(
          url.trim(),
          outputFormat,
          sourceReferenceHz,
          targetReferenceHz,
          youtubeMetadata?.title,
        )
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
    setFiles([])
    setUrl('')
    setRights(false)
    setError(null)
    setUploadProgress(null)
    if (previousId) await deleteJob(previousId).catch(() => undefined)
  }

  const stopConversion = async () => {
    if (!jobId) return
    await deleteJob(jobId).catch(() => undefined)
    setJobId(null)
    setJob(null)
    setUploadProgress(null)
    setNotice('Conversion arrêtée et fichiers temporaires supprimés.')
  }

  const stopBatch = async () => {
    batchCancelledRef.current = true
    const currentId = batchCurrentIdRef.current
    if (currentId) await deleteJob(currentId).catch(() => undefined)
  }

  const resetBatch = async () => {
    const ids = batchItems.flatMap((item) => item.jobId ? [item.jobId] : [])
    await Promise.all(ids.map((id) => deleteJob(id).catch(() => undefined)))
    setBatchItems([])
    setFiles([])
    setNotice(null)
    setError(null)
  }

  const downloadCompletedBatch = async () => {
    const ids = batchItems.flatMap((item) => (
      item.status === 'completed' && item.jobId ? [item.jobId] : []
    ))
    if (!ids.length) return
    try {
      await downloadBatch(ids)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Le téléchargement groupé a échoué.')
    }
  }

  const previewYoutube = async () => {
    if (!url.trim() || !rights) return
    setYoutubeInspecting(true)
    setYoutubeMetadata(null)
    setError(null)
    try {
      setYoutubeMetadata(await inspectYoutube(url.trim()))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'La vidéo YouTube n’a pas pu être vérifiée.')
    } finally {
      setYoutubeInspecting(false)
    }
  }

  const analyze = async () => {
    if (!canSubmit || analyzing) return
    setError(null)
    setNotice(null)
    setAnalysis(null)
    try {
      let created: { analysis_id: string }
      if (mode === 'file' && file) {
        setUploadProgress(0)
        created = await uploadAnalysis(file, setUploadProgress)
        setUploadProgress(null)
      } else {
        created = await submitYoutubeAnalysis(url.trim())
      }
      setAnalysisId(created.analysis_id)
    } catch (caught) {
      setUploadProgress(null)
      setError(caught instanceof Error ? caught.message : 'L’analyse n’a pas pu démarrer.')
    }
  }

  const resetAnalysis = async () => {
    const previousId = analysisId
    setAnalysisId(null)
    setAnalysis(null)
    setError(null)
    setUploadProgress(null)
    if (previousId) await deleteAnalysis(previousId).catch(() => undefined)
  }

  const stopAnalysis = async () => {
    if (!analysisId) return
    await deleteAnalysis(analysisId).catch(() => undefined)
    setAnalysisId(null)
    setAnalysis(null)
    setUploadProgress(null)
    setNotice('Analyse arrêtée et fichiers temporaires supprimés.')
  }

  const visibleProgress = uploadProgress ?? (feature === 'analyze' ? analysis?.progress : job?.progress) ?? 0
  const analysisStages = { download: 'Récupération de la piste audio', preparation: 'Préparation du signal', analysis: 'Analyse de l’accordage', ready: 'Analyse terminée' }
  const visibleStage = uploadProgress !== null
    ? strings.stages.upload
    : feature === 'analyze' && analysis
      ? analysisStages[analysis.stage]
      : job
        ? strings.stages[job.stage]
        : ''
  const serviceUnavailable = capabilities && !capabilities.rubberband_available

  return (
    <main className="page-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <section className="app-card" aria-labelledby="page-title">
        <header className="hero">
          <img className="brand-visual" src={`${BASE_URL}brand/musicto432-hero.webp`} alt="MusicTo432, accordage musical de 440 Hz vers 432 Hz" />
          <p className="eyebrow">MUSICAL TUNING TOOL</p>
          <h1 id="page-title">{feature === 'convert' ? <>Convertisseur musical <em>432 Hz</em></> : <>Vérifier <em>l’accordage</em></>}</h1>
          <p className="intro">{feature === 'convert' ? 'Décalez la hauteur de votre morceau de 440 vers 432 Hz, tout en conservant son tempo et sa durée.' : 'Estimez la référence d’accordage de votre morceau et découvrez s’il se rapproche de 432 Hz, de 440 Hz ou d’une autre valeur.'}</p>
        </header>

        <nav className="feature-tabs" aria-label="Fonction principale">
          <button className={feature === 'convert' ? 'active' : ''} onClick={() => setFeature('convert')}><span aria-hidden="true">↯</span> Convertir</button>
          <button className={feature === 'analyze' ? 'active' : ''} onClick={() => setFeature('analyze')}><span aria-hidden="true">◉</span> Vérifier l’accordage</button>
        </nav>

        {serviceUnavailable && <div className="alert error" role="alert">Le serveur ne possède pas le filtre Rubber Band requis. La conversion est désactivée.</div>}
        {!online && <div className="alert offline" role="status">Interface disponible hors ligne. Reconnectez le serveur pour analyser ou convertir un morceau.</div>}
        {notice && <div className="alert info" role="status">{notice}</div>}
        {error && <div className="alert error" role="alert">{error}</div>}
        {job?.status === 'failed' && <div className="alert error" role="alert">{job.error ?? 'La conversion a échoué.'}</div>}
        {analysis?.status === 'failed' && <div className="alert error" role="alert">{analysis.error ?? 'L’analyse a échoué.'}</div>}

        {feature === 'convert' && !jobId && batchItems.length === 0 && (
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
                  onDrop={(event) => { event.preventDefault(); chooseFiles(Array.from(event.dataTransfer.files)) }}
                >
                  <span className="upload-icon" aria-hidden="true">↥</span>
                  {file ? <><strong>{files.length > 1 ? `${files.length} morceaux sélectionnés` : file.name}</strong><span>{files.length > 1 ? files.map((item) => item.name).join(' · ') : `${formatBytes(file.size)} · Cliquer pour remplacer`}</span></> : <><strong>Déposez un ou plusieurs morceaux ici</strong><span>ils seront convertis successivement</span></>}
                </button>
                <input ref={inputRef} className="sr-only" type="file" multiple accept=".mp3,.wav,.flac,.m4a,.aac,.ogg,audio/*" onChange={(event) => chooseFiles(Array.from(event.target.files ?? []))} />
                <p className="formats-note">MP3, WAV, FLAC, M4A, AAC ou OGG{capabilities ? ` · ${capabilities.max_upload_mb} Mo maximum` : ''}</p>
                {localPreview && <div className="preview"><span>Original</span><audio controls src={localPreview}>Votre navigateur ne peut pas lire ce fichier.</audio></div>}
              </div>
            ) : (
              <div key="youtube-mode" className="youtube-panel">
                <label htmlFor="youtube-url">Adresse de la vidéo YouTube</label>
                <input id="youtube-url" type="url" inputMode="url" placeholder="https://youtu.be/…" value={url} onChange={(event) => { setUrl(event.target.value); setYoutubeMetadata(null) }} />
                {capabilities && !capabilities.youtube_available && <p className="inline-warning">L’import YouTube est indisponible sur ce serveur. L’import de fichier reste actif.</p>}
                <label className="rights-check"><input type="checkbox" checked={rights} onChange={(event) => setRights(event.target.checked)} /><span>Je confirme disposer des droits ou de l’autorisation nécessaires pour télécharger et transformer ce contenu.</span></label>
                <button className="inspect-button" disabled={!url.trim() || !rights || youtubeInspecting} onClick={() => void previewYoutube()}>{youtubeInspecting ? 'Vérification…' : 'Vérifier la vidéo'}</button>
                {youtubeMetadata && <div className="youtube-preview">{youtubeMetadata.thumbnail && <img src={youtubeMetadata.thumbnail} alt="" referrerPolicy="no-referrer" />}<div><strong>{youtubeMetadata.title}</strong><span>{youtubeMetadata.uploader ?? 'Créateur inconnu'} · {formatDuration(youtubeMetadata.duration)}</span><small>Vidéo vérifiée avant traitement</small></div></div>}
              </div>
            )}

            <fieldset className="frequency-options">
              <legend>Changement d’accordage</legend>
              <div className="frequency-grid">
                <label><span>Fréquence source</span><div><button type="button" className={sourceReferenceHz === 432 ? 'selected' : ''} onClick={() => setSourceReferenceHz(432)}>432</button><button type="button" className={sourceReferenceHz === 440 ? 'selected' : ''} onClick={() => setSourceReferenceHz(440)}>440</button><input type="number" min="400" max="480" step="0.1" aria-label="Fréquence source personnalisée" value={sourceReferenceHz} onChange={(event) => setSourceReferenceHz(Number(event.target.value))} /><b>Hz</b></div></label>
                <span className="frequency-arrow" aria-hidden="true">→</span>
                <label><span>Fréquence cible</span><div><button type="button" className={targetReferenceHz === 432 ? 'selected' : ''} onClick={() => setTargetReferenceHz(432)}>432</button><button type="button" className={targetReferenceHz === 440 ? 'selected' : ''} onClick={() => setTargetReferenceHz(440)}>440</button><input type="number" min="400" max="480" step="0.1" aria-label="Fréquence cible personnalisée" value={targetReferenceHz} onChange={(event) => setTargetReferenceHz(Number(event.target.value))} /><b>Hz</b></div></label>
              </div>
              {!validFrequencyChange && <p className="inline-warning">Choisissez deux fréquences différentes, comprises entre 400 et 480 Hz.</p>}
            </fieldset>

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

            <button className="primary-button" disabled={!canSubmit || Boolean(serviceUnavailable)} onClick={() => void convert()}><span>Convertir vers {targetReferenceHz} Hz</span><span aria-hidden="true">→</span></button>
          </>
        )}

        {feature === 'convert' && jobId && job?.status !== 'completed' && (
          <section className="progress-panel" aria-live="polite">
            <div className="vinyl" aria-hidden="true"><div /></div>
            <p className="stage">{visibleStage || 'Mise en file d’attente'}</p>
            <p className="progress-value">{visibleProgress}<small>%</small></p>
            <progress max="100" value={visibleProgress}>{visibleProgress}%</progress>
            <p className="patience">Gardez cette page ouverte pendant le traitement.</p>
            {(job?.status === 'queued' || job?.status === 'processing') && <button className="stop-button" onClick={() => void stopConversion()}>■ Arrêter la conversion</button>}
            {job?.status === 'failed' && <button className="secondary-button" onClick={() => void reset()}>Réessayer avec un autre morceau</button>}
          </section>
        )}

        {feature === 'convert' && job?.status === 'completed' && (
          <section className="result-panel" aria-live="polite">
            <div className="success-icon" aria-hidden="true">✓</div>
            <p className="eyebrow">CONVERSION TERMINÉE</p>
            <h2>Votre morceau est prêt</h2>
            <p>Hauteur déplacée de {(1200 * Math.log2(job.target_reference_hz / job.source_reference_hz)).toFixed(2)} cents, durée et tempo préservés.</p>
            <div className="preview result"><span>Résultat {job.target_reference_hz} Hz</span><audio controls src={downloadUrl(job.job_id)}>Votre navigateur ne peut pas lire ce fichier.</audio></div>
            <a className="primary-button" href={downloadUrl(job.job_id)} download={job.download_name ?? undefined}><span>Télécharger le fichier</span><span aria-hidden="true">↓</span></a>
            <button className="secondary-button new-track-button" onClick={() => void reset()}>＋ Convertir un autre morceau</button>
            {job.expires_at && <small className="expiry">Téléchargement disponible temporairement.</small>}
          </section>
        )}

        {feature === 'convert' && batchItems.length > 0 && (
          <section className="batch-panel" aria-live="polite">
            <div className="batch-heading"><div><p className="eyebrow">FILE DE CONVERSION</p><h2>{batchItems.filter((item) => item.status === 'completed').length} / {batchItems.length} terminés</h2></div>{batchRunning && <button className="stop-button compact" onClick={() => void stopBatch()}>■ Tout arrêter</button>}</div>
            <div className="batch-list">
              {batchItems.map((item, index) => (
                <article key={`${item.name}-${index}`} className={`batch-item status-${item.status}`}>
                  <div className="batch-state" aria-hidden="true">{item.status === 'completed' ? '✓' : item.status === 'failed' ? '!' : item.status === 'stopped' ? '■' : index + 1}</div>
                  <div className="batch-details"><strong>{item.name}</strong><span>{item.status === 'waiting' ? 'En attente' : item.status === 'uploading' ? 'Envoi du fichier' : item.status === 'processing' ? `Conversion · ${item.progress}%` : item.status === 'completed' ? 'Terminé' : item.status === 'stopped' ? 'Arrêté' : item.error ?? 'Échec'}</span>{['uploading','processing'].includes(item.status) && <progress max="100" value={item.progress}>{item.progress}%</progress>}</div>
                  {item.status === 'completed' && item.jobId && <a className="batch-download" href={downloadUrl(item.jobId)} download={item.downloadName ?? undefined} aria-label={`Télécharger ${item.name}`}>↓</a>}
                </article>
              ))}
            </div>
            {!batchRunning && batchItems.some((item) => item.status === 'completed') && <button className="primary-button batch-zip-button" onClick={() => void downloadCompletedBatch()}><span>Télécharger tous les résultats</span><span aria-hidden="true">ZIP ↓</span></button>}
            {!batchRunning && <button className="secondary-button new-track-button" onClick={() => void resetBatch()}>＋ Convertir d’autres morceaux</button>}
          </section>
        )}

        {feature === 'analyze' && !analysisId && (
          <section className="analysis-start">
            <div className="tabs" role="tablist" aria-label="Source à analyser">
              <button role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'active' : ''} onClick={() => setMode('file')}>Fichier audio</button>
              <button role="tab" aria-selected={mode === 'youtube'} className={mode === 'youtube' ? 'active' : ''} onClick={() => setMode('youtube')}>Lien YouTube</button>
            </div>

            {mode === 'file' ? (
              <div key="analysis-file-mode">
                <button
                  type="button"
                  className={`drop-zone ${file ? 'has-file' : ''}`}
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files[0]) }}
                >
                  <span className="upload-icon" aria-hidden="true">⌁</span>
                  {file ? <><strong>{file.name}</strong><span>{formatBytes(file.size)} · Cliquer pour remplacer</span></> : <><strong>Choisissez un morceau à analyser</strong><span>ou déposez-le dans cette zone</span></>}
                </button>
                <input ref={inputRef} className="sr-only" type="file" accept=".mp3,.wav,.flac,.m4a,.aac,.ogg,audio/*" onChange={(event) => chooseFile(event.target.files?.[0])} />
                <p className="formats-note">L’analyse utilise plusieurs passages contenant des notes stables.</p>
                {localPreview && <div className="preview"><span>Morceau à analyser</span><audio controls src={localPreview}>Votre navigateur ne peut pas lire ce fichier.</audio></div>}
              </div>
            ) : (
              <div key="analysis-youtube-mode" className="youtube-panel">
                <label htmlFor="analysis-youtube-url">Adresse de la vidéo YouTube</label>
                <input id="analysis-youtube-url" type="url" inputMode="url" placeholder="https://youtu.be/…" value={url} onChange={(event) => { setUrl(event.target.value); setYoutubeMetadata(null) }} />
                {capabilities && !capabilities.youtube_available && <p className="inline-warning">L’import YouTube est indisponible sur ce serveur.</p>}
                <label className="rights-check"><input type="checkbox" checked={rights} onChange={(event) => setRights(event.target.checked)} /><span>Je confirme disposer des droits ou de l’autorisation nécessaires pour télécharger et analyser ce contenu.</span></label>
                <button className="inspect-button" disabled={!url.trim() || !rights || youtubeInspecting} onClick={() => void previewYoutube()}>{youtubeInspecting ? 'Vérification…' : 'Vérifier la vidéo'}</button>
                {youtubeMetadata && <div className="youtube-preview">{youtubeMetadata.thumbnail && <img src={youtubeMetadata.thumbnail} alt="" referrerPolicy="no-referrer" />}<div><strong>{youtubeMetadata.title}</strong><span>{youtubeMetadata.uploader ?? 'Créateur inconnu'} · {formatDuration(youtubeMetadata.duration)}</span><small>Vidéo vérifiée avant analyse</small></div></div>}
              </div>
            )}

            <div className="analysis-note"><span aria-hidden="true">i</span><p>L’application estime une référence musicale globale. Un morceau très percussif, bruité ou volontairement désaccordé peut produire un résultat incertain.</p></div>
            <button className="primary-button" disabled={!canSubmit} onClick={() => void analyze()}><span>Analyser l’accordage</span><span aria-hidden="true">→</span></button>
          </section>
        )}

        {feature === 'analyze' && analysisId && analysis?.status !== 'completed' && (
          <section className="progress-panel" aria-live="polite">
            <div className="spectrum-loader" aria-hidden="true">{[1,2,3,4,5,6,7,8,9].map((item) => <i key={item} />)}</div>
            <p className="stage">{visibleStage || 'Mise en file d’attente'}</p>
            <p className="progress-value">{visibleProgress}<small>%</small></p>
            <progress max="100" value={visibleProgress}>{visibleProgress}%</progress>
            <p className="patience">Recherche d’une référence commune dans plusieurs passages.</p>
            {(analysis?.status === 'queued' || analysis?.status === 'processing') && <button className="stop-button" onClick={() => void stopAnalysis()}>■ Arrêter l’analyse</button>}
            {analysis?.status === 'failed' && <button className="secondary-button" onClick={() => void resetAnalysis()}>Analyser un autre morceau</button>}
          </section>
        )}

        {feature === 'analyze' && analysis?.status === 'completed' && analysis.result && (
          <section className="analysis-result" aria-live="polite">
            <p className="eyebrow">RÉFÉRENCE ESTIMÉE</p>
            <div className="frequency-reading"><strong>{analysis.result.estimated_reference_hz.toFixed(1)}</strong><span>Hz</span></div>
            <p className={`classification class-${analysis.result.classification}`}>{analysis.result.explanation}</p>
            <div className="tuning-scale" aria-label={`Référence estimée ${analysis.result.estimated_reference_hz.toFixed(1)} hertz`}>
              <div className="scale-track"><i className="marker marker-432" /><i className="marker marker-440" /><i className="estimate" style={{ left: `${Math.min(100, Math.max(0, (analysis.result.estimated_reference_hz - 428) / 25 * 100))}%` }} /></div>
              <div className="scale-labels"><span>428</span><b>432 Hz</b><b>440 Hz</b><span>453</span></div>
            </div>
            <div className="analysis-metrics">
              <div><span>Écart avec 440 Hz</span><strong>{analysis.result.offset_from_440_cents > 0 ? '+' : ''}{analysis.result.offset_from_440_cents.toFixed(1)} cents</strong></div>
              <div><span>Écart avec 432 Hz</span><strong>{analysis.result.offset_from_432_cents > 0 ? '+' : ''}{analysis.result.offset_from_432_cents.toFixed(1)} cents</strong></div>
              <div><span>Confiance</span><strong>{analysis.result.confidence}%</strong></div>
            </div>
            <div className="confidence-bar"><i style={{ width: `${analysis.result.confidence}%` }} /></div>
            {analysis.result.classification !== 'uncertain' && <button className="primary-button" onClick={() => { setSourceReferenceHz(analysis.result!.estimated_reference_hz); setTargetReferenceHz(432); setFeature('convert') }}><span>Convertir ce morceau vers 432 Hz</span><span aria-hidden="true">→</span></button>}
            <button className="secondary-button new-track-button" onClick={() => void resetAnalysis()}>＋ Analyser un autre morceau</button>
          </section>
        )}

        <footer><span>{feature === 'convert' ? `${sourceReferenceHz} → ${targetReferenceHz}` : '432 · 440'}</span><p>{feature === 'convert' ? 'La conversion applique un décalage relatif sans modifier le tempo.' : 'L’estimation dépend des notes stables réellement présentes dans le morceau.'}</p></footer>
      </section>
    </main>
  )
}

export default App
