import '@testing-library/jest-dom/vitest'

Object.defineProperty(URL, 'createObjectURL', { value: () => 'blob:test' })
Object.defineProperty(URL, 'revokeObjectURL', { value: () => undefined })

