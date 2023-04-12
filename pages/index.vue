<!--
  Copyright (c) Tibor Völcker <tibor.voelcker@hotmail.de>
  Created on 08.04.2023
-->
<template>
  <Header />
  <div id="overview">
    <Card color="var(--brand3)">
      <CardDescription>Current surplus</CardDescription>
      <CardValue>501.6</CardValue>
    </Card>
    <Card color="var(--brand1)">
      <CardDescription>Free to spend</CardDescription>
      <CardValue>1041.51</CardValue>
    </Card>
    <Card color="var(--brand2)">
      <CardDescription>Ø Monthly Fixed Expenses</CardDescription>
      <CardValue>50.12</CardValue>
      <CardDescription>Due this month</CardDescription>
      <CardValue>19.79</CardValue>
    </Card>
  </div>
  <div id="transactions">
    <p>Transactions</p>
    <Table :headers="headers" :data="data" :startColor="1" :styles="styles" />
  </div>
</template>

<script setup>
let headers = ["Description", "Value", "Leisure Expense?"];
let data = [
  ["Expense1", "-101.50€", false],
  ["Expense2", "-24.99€", false],
  ["Expense3", "-2.13€", true],
];
let styles = [
  {},
  { textAlign: "right", maxWidth: "150px" },
  {
    textAlign: "center",
    maxWidth: "250px",
  },
];
</script>

<style>
#overview {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 32px;
  gap: 20px;
}

#transactions {
  padding: 16px 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}
#transactions > p {
  margin: 0;
  font-weight: 700;
  font-size: 36px;
}
</style>
