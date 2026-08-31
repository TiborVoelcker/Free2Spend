<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 08.04.2023
-->
<template>
  <img id="logo" src="~/assets/Logo.svg" alt="Logo" />
  <Input icon="account_circle" color="var(--brand3)" placeholder="Username" />
  <Input icon="lock" color="var(--brand1)" placeholder="Password" />
  <Button color="var(--brand2)">Login</Button>
</template>

<style>
body > div {
  align-items: center;
  justify-content: center;
  gap: 40px;
}
</style>

<style scoped>
#logo {
  width: 170px;
  height: 80px;
}
</style>
