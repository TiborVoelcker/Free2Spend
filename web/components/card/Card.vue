<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <div class="overview-card">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  color: string;
}>();
</script>

<style scoped>
.overview-card {
  width: 100%;
  height: 100%;
  max-width: 350px;
  background: var(--text-shade);
  border-radius: 20px;
  padding: 12px 16px;
  color: v-bind(color);
  display: grid;
}
</style>
