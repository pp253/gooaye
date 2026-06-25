import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL as string,
  import.meta.env.VITE_SUPABASE_ANON_KEY as string,
)

/**
 * PostgREST 單次查詢上限 1000 列；分頁撈出符合條件的全部資料。
 * `page(offset, limit)` 回傳該頁資料，回傳列數 < limit 視為撈完。
 */
export async function fetchAllPaged<T>(
  page: (offset: number, limit: number) => PromiseLike<{ data: T[] | null }>,
  pageSize = 1000,
): Promise<T[]> {
  const all: T[] = []
  for (let offset = 0; ; offset += pageSize) {
    const { data } = await page(offset, pageSize)
    const rows = data ?? []
    all.push(...rows)
    if (rows.length < pageSize) break
  }
  return all
}
