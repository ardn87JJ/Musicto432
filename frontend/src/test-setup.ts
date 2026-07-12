import '@testing-library/jest-dom/vitest'

Object.defineProperty(URL, 'createObjectURL', { value: () => 'blob:test' })
Object.defineProperty(URL, 'revokeObjectURL', { value: () => undefined })
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
})
