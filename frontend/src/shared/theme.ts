/**
 * 亮/暗主题。
 *
 * 优先级：localStorage 里用户的选择 > 系统偏好。
 * 首屏在 main.ts 里调用 initTheme()，避免闪白。
 */

import { ref } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'msc-theme'

function systemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function stored(): Theme | null {
  const value = localStorage.getItem(STORAGE_KEY)
  return value === 'light' || value === 'dark' ? value : null
}

export const theme = ref<Theme>('light')

function apply(next: Theme) {
  theme.value = next
  document.documentElement.dataset.theme = next
}

function fromUrl(): Theme | null {
  const value = new URLSearchParams(location.search).get('theme')
  return value === 'light' || value === 'dark' ? value : null
}

export function initTheme() {
  apply(fromUrl() ?? stored() ?? systemTheme())
  // 用户没手动选过时，跟随系统变化
  window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
    if (!stored()) apply(event.matches ? 'dark' : 'light')
  })
}

export function toggleTheme() {
  const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(STORAGE_KEY, next)
  apply(next)
}
