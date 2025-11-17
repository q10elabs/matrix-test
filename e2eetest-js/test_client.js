const sdk = require("matrix-js-sdk");

const client = sdk.createClient({
  baseUrl: "http://localhost:8008",
  userId: "@test:localhost",
  deviceId: "test",
  store: new sdk.MemoryStore(),
});

console.log("Client methods starting with 's':");
Object.getOwnPropertyNames(Object.getPrototypeOf(client))
  .filter(m => m.startsWith('s') && !m.startsWith('_'))
  .forEach(m => console.log(m));

console.log("\nClient methods starting with 'j':");
Object.getOwnPropertyNames(Object.getPrototypeOf(client))
  .filter(m => m.startsWith('j') && !m.startsWith('_'))
  .forEach(m => console.log(m));

console.log("\nClient methods starting with 'send':");
Object.getOwnPropertyNames(Object.getPrototypeOf(client))
  .filter(m => m.startsWith('send') && !m.startsWith('_'))
  .forEach(m => console.log(m));
