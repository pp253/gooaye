import { computed, type Ref } from 'vue'
import { TRADEABLE_TYPES } from '@/types/core'
import type { StockRow } from '@/types/stock'

export function useStockFiltering(
  rows: Ref<StockRow[]>,
  config: {
    assetView: Ref<'tradeable' | 'theme' | 'all'>
    market: Ref<'ALL' | 'TW' | 'US'>
    onlyPosition?: Ref<boolean>
    hideStale?: Ref<boolean>
    search?: Ref<string>
    sortBy?: Ref<string>
  },
) {
  const filtered = computed(() => {
    let list = rows.value.slice()
    if (config.assetView.value === 'tradeable') {
      list = list.filter((r) => TRADEABLE_TYPES.includes(r.asset_type))
    } else if (config.assetView.value === 'theme') {
      list = list.filter((r) => !TRADEABLE_TYPES.includes(r.asset_type))
    }
    if (config.market.value !== 'ALL') {
      list = list.filter((r) => r.market === config.market.value)
    }
    if (config.onlyPosition?.value) {
      list = list.filter((r) => r.signal.has_position_ever)
    }
    if (config.hideStale?.value) {
      list = list.filter((r) => r.signal.latest_freshness !== 'stale')
    }

    if (config.search?.value) {
      const q = config.search.value.trim().toLowerCase()
      if (q) {
        list = list.filter(
          (r) =>
            r.ticker.toLowerCase().includes(q) ||
            r.name_zh.toLowerCase().includes(q) ||
            (r.name_en?.toLowerCase().includes(q) ?? false) ||
            r.aliases.some((a) => a.toLowerCase().includes(q)),
        )
      }
    }

    if (config.sortBy?.value) {
      const sortBy = config.sortBy.value
      list.sort((a, b) => {
        if (sortBy === 'score') return b.signal.score - a.signal.score
        if (sortBy === 'recent') return a.signal.latest_days_ago - b.signal.latest_days_ago
        if (sortBy === 'first_mention')
          return a.signal.first_mention_days_ago - b.signal.first_mention_days_ago
        return b.signal.mention_count - a.signal.mention_count
      })
    }
    return list
  })

  return { filtered }
}
