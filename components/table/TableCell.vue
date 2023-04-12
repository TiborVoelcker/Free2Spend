<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <span v-if="typeof data === 'boolean'" class="cell material-symbols-outlined">
    check_circle
  </span>
  <div v-else class="cell">{{ data }}</div>
</template>

<script setup lang="ts">
defineProps<{
  data: string | boolean;
}>();
</script>

<style scoped>
.cell {
  flex: 1;
}
</style>
