<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 12.04.2023
-->
<template>
  <header>
    <img id="logo" src="~/assets/Logo.svg" alt="Logo" />
    <span class="material-symbols-outlined"> settings </span>
  </header>
</template>

<style scoped>
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
}

#logo {
  width: 136px;
  height: 64px;
}

header > .material-symbols-outlined {
  color: var(--brand1);
  font-size: 40px;
}
</style>
