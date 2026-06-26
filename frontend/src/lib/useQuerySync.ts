import { watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface Field<T = unknown> {
  ref: Ref<T>
  default: T
}

/**
 * 把一組 reactive state 雙向同步到網址 query string，讓使用者重新整理／返回時保留狀態。
 *
 * - 初始化時從 URL 讀回 state
 * - state 變動時以 router.replace 寫回 URL（等於預設值者省略，保持網址乾淨）
 * - 支援 string 與 boolean（boolean 以 1/0 表示）
 */
export function useQuerySync(fields: Record<string, Field>): void {
  const route = useRoute()
  const router = useRouter()

  // 1. 從 URL 初始化
  for (const [key, f] of Object.entries(fields)) {
    const q = route.query[key]
    if (q == null) continue
    const raw = Array.isArray(q) ? q[0] : q
    if (raw == null) continue
    f.ref.value = typeof f.default === 'boolean' ? raw === '1' || raw === 'true' : raw
  }

  // 2. state -> URL
  const refs = Object.values(fields).map((f) => f.ref)
  watch(refs, () => {
    const query: Record<string, string> = { ...(route.query as Record<string, string>) }
    for (const [key, f] of Object.entries(fields)) {
      const v = f.ref.value
      if (v === f.default) delete query[key]
      else query[key] = typeof v === 'boolean' ? (v ? '1' : '0') : String(v)
    }
    router.replace({ query })
  })
}
