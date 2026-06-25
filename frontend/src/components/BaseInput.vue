<script setup lang="ts">
const model = defineModel<string>({ default: '' })

defineProps<{
  placeholder?: string
  type?: string
  required?: boolean
}>()
</script>

<template>
  <input
    v-model="model"
    :type="type || 'text'"
    :placeholder="placeholder"
    :required="required"
    class="input-field"
  />
</template>

<style scoped>
.input-field {
  display: block;
  width: 100%;
  max-width: 320px;
  margin-bottom: 1rem;
  padding: 0.45rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #2d3748;
  background: #1a1f2e;
  color: #e2e8f0;
  font-size: 0.88rem;
  transition: border-color 0.15s;
}
.input-field::placeholder {
  color: #718096;
}
.input-field:focus {
  outline: none;
  border-color: #63b3ed;
}
</style>
