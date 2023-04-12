<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 08.04.2023
-->
<template>
  <Header />
  <div id="fixed-expenses">
    <p>Fixed Expenses</p>
    <Table :headers="headers" :data="data" :startColor="1" :styles="styles" />
  </div>
</template>

<script setup>
let headers = ["Description", "Value", "Date", "Interval"];
let data = [
  ["Income1", "102.52€", "10.12.2023", "monthly"],
  ["Expense1", "-15.00€", "3.9.2021", "yearly"],
  ["Expense2", "-6.10€", "8.9.2022", "biweekly"],
];
let styles = [
  {},
  { textAlign: "right", maxWidth: "150px" },
  {
    textAlign: "right",
    maxWidth: "250px",
  },
  { textAlign: "center", maxWidth: "250px" },
];
</script>

<style scoped>
#fixed-expenses {
  padding: 16px 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

#fixed-expenses > p {
  margin: 0;
  font-weight: 700;
  font-size: 36px;
}
</style>
