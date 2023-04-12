<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 09.04.2023
-->
<template>
  <template v-if="icon">
    <div class="icon-input">
      <input class="text-input" :placeholder="placeholder" />
      <i class="material-symbols-outlined" aria-hidden="true">{{ icon }} </i>
    </div>
  </template>
  <template v-else>
    <input class="text-input" :placeholder="placeholder" />
  </template>
</template>

<script setup lang="ts">
defineProps<{
  placeholder?: string;
  icon?: string;
  color?: string;
}>();
</script>

<style scoped>
input {
  outline: none;
  border: none;
  background: var(--text-shade);
  width: 300px;
  height: 32px;
  border-radius: 16px;
  padding-left: 16px;
}

input::placeholder {
  font-style: italic;
  color: var(--background);
}

.icon-input {
  position: relative;
}

.icon-input .text-input {
  padding-left: 40px;
}

.icon-input i {
  position: absolute;
  left: 0;
  padding: 4px;
  border-radius: 16px;
  color: v-bind(color);
  transition: none;
  padding-right: 272px;
  pointer-events: none;
}

.icon-input .text-input:focus + i {
  background-color: v-bind(color);
  color: var(--background-shade);
  padding-right: 4px;
  transition: 0.4s ease-out;
}
</style>
