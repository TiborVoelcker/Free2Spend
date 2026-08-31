<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 09.04.2023
-->
<template>
  <button><slot /></button>
</template>

<script setup lang="ts">
const props = defineProps<{
  color: string;
}>();
</script>

<style scoped>
button {
  width: 125px;
  height: 32px;
  border-radius: 32px;
  border: 0;
  background: v-bind(color);
  color: var(--background-shade);
}
</style>
