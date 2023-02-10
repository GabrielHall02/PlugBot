When restarting db need to create index

db.landohub.CheckoutSessions.createIndex({ "createdAt": 1 }, { expireAfterSeconds: 900, partialFilterExpression: { "status": "pending" } });