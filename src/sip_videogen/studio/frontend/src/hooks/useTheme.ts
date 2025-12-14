import { useEffect } from 'react'

export function useTheme() {
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')

    const apply = (isDark: boolean) => {
      document.documentElement.classList.toggle('dark', isDark)
    }

    apply(mq.matches)

    const handler = (e: MediaQueryListEvent) => apply(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
}
