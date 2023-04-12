<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <div :class="['row', header ? 'header' : '']">
    <TableCell
      v-for="(cell, i) in data"
      :data="cell"
      :style="[
        styles?.[i] || {},
        {
          color:
            header || (typeof cell === 'boolean' && cell)
              ? colors[i]
              : 'inherit',
        },
      ]"
    />
  </div>
</template>

<script setup lang="ts">
import { StyleValue } from "vue";

defineProps<{
  header?: boolean;
  data: (string | boolean)[];
  colors: string[];
  styles?: StyleValue[];
}>();
</script>

<style scoped>
.row {
  display: flex;
  padding: 0 16px;
  height: 64px;
  align-items: center;
  gap: 8px;
}

.header {
  background: var(--text-shade);
}
</style>
