<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <div class="table">
    <TableRow
      :header="true"
      :colors="colors"
      :data="headers"
      :styles="styles"
    />
    <TableRow
      v-for="row in data"
      :colors="colors"
      :data="row"
      :styles="styles"
    />
  </div>
</template>

<script setup lang="ts">
import { StyleValue } from "vue";

const props = defineProps<{
  headers: string[];
  data: (string | boolean)[][];
  startColor?: number;
  styles?: StyleValue[];
}>();

let colors = props.headers.map(
  (_, i) => `var(--brand${((i + (props.startColor || 0)) % 3) + 1})`
);
</script>
