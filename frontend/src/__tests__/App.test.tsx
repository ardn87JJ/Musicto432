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
    expect(screen.getByText('Déposez votre morceau ici')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Convertir en 432 Hz/ })).toBeDisabled()
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/capabilities'))
  })

  it('rejette une extension non audio', async () => {
    render(<App />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const invalid = new File(['danger'], 'virus.exe', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [invalid] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Format non accepté')
  })

  it('exige la confirmation des droits pour YouTube', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    const button = screen.getByRole('button', { name: /Convertir en 432 Hz/ })
    expect(button).toBeDisabled()
    await user.click(screen.getByRole('checkbox'))
    await waitFor(() => expect(button).toBeEnabled())
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
        }),
      } as Response
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('tab', { name: 'Lien YouTube' }))
    await user.type(screen.getByLabelText('Adresse de la vidéo YouTube'), 'https://youtu.be/abcdefghijk')
    await user.click(screen.getByRole('checkbox'))
    await user.click(await screen.findByRole('button', { name: /Convertir en 432 Hz/ }))
    expect(await screen.findByRole('heading', { name: 'Votre morceau est prêt' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Télécharger le fichier/ })).toHaveAttribute(
      'href',
      `/api/jobs/${'a'.repeat(32)}/download`,
    )
  })
})
