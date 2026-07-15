import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)

// Nettoie les anciens éléments PWA installés par les versions 0.5/0.6.
if ('serviceWorker' in navigator) {
  const applicationScope = new URL(import.meta.env.BASE_URL, window.location.origin).href
  void navigator.serviceWorker.getRegistrations().then((registrations) => (
    Promise.all(
      registrations
        .filter((registration) => registration.scope.startsWith(applicationScope))
        .map((registration) => registration.unregister()),
    )
  ))
}
if ('caches' in window) {
  void caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith('musicto432-')).map((key) => caches.delete(key)),
  ))
}
