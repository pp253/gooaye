<script setup lang="ts">
import InfoTip from '@/components/InfoTip.vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string
    subtitle?: string
    color?: string
    /** 副數值（如台股/美股分拆） */
    secondary?: { label: string; value: string; color?: string }[]
    /** 是否顯示 ⓘ tooltip 插槽 */
    hasTip?: boolean
  }>(),
  { color: '#e2e8f0', hasTip: false },
)
</script>

<template>
  <div class="kpi-card">
    <div class="kpi-header">
      <span class="kpi-label">{{ label }}</span>
      <InfoTip v-if="hasTip">
        <slot name="tip" />
      </InfoTip>
    </div>
    <div class="kpi-value" :style="{ color }">{{ value }}</div>
    <div v-if="subtitle" class="kpi-subtitle">{{ subtitle }}</div>
    <div v-if="secondary?.length" class="kpi-secondary">
      <span v-for="s in secondary" :key="s.label" class="kpi-sec-item">
        <span class="kpi-sec-label">{{ s.label }}</span>
        <span class="kpi-sec-val" :style="{ color: s.color ?? '#a0aec0' }">{{ s.value }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  background: #1a1f2e;
  border: 1px solid #2d3748;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  transition: border-color 0.2s;
}
.kpi-card:hover {
  border-color: #4a5568;
}
.kpi-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.kpi-label {
  font-size: 0.74rem;
  color: #718096;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.kpi-value {
  font-size: 1.85rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.kpi-subtitle {
  font-size: 0.72rem;
  color: #4a5568;
}
.kpi-secondary {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.15rem;
  flex-wrap: wrap;
}
.kpi-sec-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.kpi-sec-label {
  font-size: 0.68rem;
  color: #4a5568;
}
.kpi-sec-val {
  font-size: 0.75rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
