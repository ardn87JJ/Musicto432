import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const capabilities = {
  input_formats: ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg'],
  output_formats: ['mp3', 'wav', 'flac'],
  max_upload_mb: 250,
  max_duration_seconds: 3600,
  youtube_available: true,
  rubberband_available: true,
}

describe('App', () => {
  afterEach(() => cleanup())

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => capabilities }))
  })

  it('affiche le parcours fichier par défaut', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /Convertisseur musical 432 Hz/i })).toBeInTheDocument()
    expect(screen.getByText('Déposez un ou plusieurs morceaux ici')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Convertir vers 432 Hz/ })).toBeDisabled()
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/capabilities'))
  })

  it('ne propose plus l’installation et indique le mode hors ligne', async () => {
    render(<App />)
    expect(screen.queryByRole('button', { name: 'Installer' })).not.toBeInTheDocument()
    expect(screen.queryByText('Installer MusicTo432')).not.toBeInTheDocument()
    window.dispatchEvent(new Event('offline'))
    expect(await screen.findByText(/Interface disponible hors ligne/)).toBeInTheDocument()
  })

  it('rejette une extension non audio', async () => {
    render(<App />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const invalid = new File(['danger'], 'virus.exe', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [invalid] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('n’est pas accepté')
  })

  it('accepte plusieurs fichiers dans une file successive', async () => {
    const user = userEvent.setup()
    render(<App />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, [
      new File(['audio-a'], 'premier.mp3', { type: 'audio/mpeg' }),
      new File(['audio-b'], 'second.mp3', { type: 'audio/mpeg' }),
    ])
    expect(screen.getByText('2 morceaux sélectionnés')).toBeInTheDocument()
    expect(screen.getByText(/premier.mp3.*second.mp3/)).toBeInTheDocument()
  })

  it('exige la confirmation des droits pour YouTube', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    const button = screen.getByRole('button', { name: /Convertir vers 432 Hz/ })
    expect(button).toBeDisabled()
    await user.click(screen.getByRole('checkbox'))
    await waitFor(() => expect(button).toBeEnabled())
  })

  it('permet de choisir une fréquence cible personnalisée', async () => {
    const user = userEvent.setup()
    render(<App />)
    const target = screen.getByLabelText('Fréquence cible personnalisée')
    await user.clear(target)
    await user.type(target, '444')
    expect(screen.getByRole('button', { name: /Convertir vers 444 Hz/ })).toBeDisabled()
  })

  it('prévisualise les informations YouTube avant traitement', async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      const target = String(input)
      if (target.endsWith('/api/capabilities')) {
        return { ok: true, json: async () => capabilities } as Response
      }
      return {
        ok: true,
        json: async () => ({
          title: 'Morceau de référence',
          uploader: 'Artiste test',
          duration: 185,
          thumbnail: null,
          webpage_url: 'https://youtu.be/abcdefghijk',
        }),
      } as Response
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Vérifier la vidéo' }))
    expect(await screen.findByText('Morceau de référence')).toBeInTheDocument()
    expect(screen.getByText(/Artiste test · 3:05/)).toBeInTheDocument()
  })

  it('désactive la conversion si Rubber Band manque', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...capabilities, rubberband_available: false }),
    } as Response)
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Rubber Band')
  })

  it('affiche le lecteur et le téléchargement après réussite', async () => {
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const target = String(input)
      if (target.endsWith('/api/capabilities')) {
        return { ok: true, json: async () => capabilities } as Response
      }
      if (target.endsWith('/api/jobs/youtube') && init?.method === 'POST') {
        return { ok: true, json: async () => ({ job_id: 'a'.repeat(32) }) } as Response
      }
      return {
        ok: true,
        json: async () => ({
          job_id: 'a'.repeat(32),
          status: 'completed',
          progress: 100,
          stage: 'ready',
          error: null,
          expires_at: '2026-07-12T23:00:00Z',
          download_name: 'youtube-audio_432Hz.mp3',
          source_reference_hz: 440,
          target_reference_hz: 432,
        }),
      } as Response
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    await user.click(screen.getByRole('checkbox'))
    await user.click(await screen.findByRole('button', { name: /Convertir vers 432 Hz/ }))
    expect(await screen.findByRole('heading', { name: 'Votre morceau est prêt' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Télécharger le fichier/ })).toHaveAttribute(
      'href',
      `/api/jobs/${'a'.repeat(32)}/download`,
    )
  })

  it('analyse également un lien YouTube et affiche la référence estimée', async () => {
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const target = String(input)
      if (target.endsWith('/api/capabilities')) {
        return { ok: true, json: async () => capabilities } as Response
      }
      if (target.endsWith('/api/analysis/youtube') && init?.method === 'POST') {
        return { ok: true, json: async () => ({ analysis_id: 'b'.repeat(32) }) } as Response
      }
      return {
        ok: true,
        json: async () => ({
          analysis_id: 'b'.repeat(32),
          status: 'completed',
          progress: 100,
          stage: 'ready',
          error: null,
          expires_at: '2026-07-12T23:00:00Z',
          result: {
            estimated_reference_hz: 432.2,
            offset_from_440_cents: -30.97,
            offset_from_432_cents: 0.8,
            classification: '432',
            confidence: 84,
            analyzed_seconds: 60,
            diagnostic: 'stable',
            explanation: 'Le morceau semble accordé autour de La = 432 Hz.',
          },
        }),
      } as Response
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /Vérifier l’accordage/ }))
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    await user.click(screen.getByRole('checkbox'))
    await user.click(await screen.findByRole('button', { name: 'Analyser l’accordage' }))
    expect(await screen.findByText('432.2')).toBeInTheDocument()
    expect(screen.getByText(/semble accordé autour de La = 432 Hz/)).toBeInTheDocument()
    expect(screen.getByText('84%')).toBeInTheDocument()
  })
})
