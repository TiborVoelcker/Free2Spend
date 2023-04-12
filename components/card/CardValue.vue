<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <p class="value"><slot />€</p>
</template>

<style scoped>
.value {
  position: relative;
  justify-self: center;
  margin: 0;
  font-weight: 300;
  font-size: 6cqw;
}
</style>
