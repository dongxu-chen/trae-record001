const express = require('express');
const https = require('https');
const fs = require('fs');
const app = express();

app.use(express.json());

const USERS = {
  '1': { id: '1', name: 'Alice', email: 'alice@example.com', role: 'admin' },
  '2': { id: '2', name: 'Bob', email: 'bob@example.com', role: 'user' },
  '3': { id: '3', name: 'Charlie', email: 'charlie@example.com', role: 'user' },
};

const PRODUCTS = {
  '101': { id: '101', name: 'Widget Pro', price: 99.99, stock: 100 },
  '102': { id: '102', name: 'Gadget Plus', price: 149.99, stock: 50 },
};

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'production' });
});

app.get('/api/users', (req, res) => {
  res.json(Object.values(USERS));
});

app.get('/api/users/:id', (req, res) => {
  const user = USERS[req.params.id];
  if (user) {
    res.json(user);
  } else {
    res.status(404).json({ error: 'User not found' });
  }
});

app.post('/api/users', (req, res) => {
  const { name, email, role } = req.body;
  const id = String(Date.now());
  USERS[id] = { id, name, email, role: role || 'user' };
  res.status(201).json(USERS[id]);
});

app.get('/api/products', (req, res) => {
  res.json(Object.values(PRODUCTS));
});

app.get('/api/products/:id', (req, res) => {
  const product = PRODUCTS[req.params.id];
  if (product) {
    res.json(product);
  } else {
    res.status(404).json({ error: 'Product not found' });
  }
});

app.post('/api/orders', (req, res) => {
  const { userId, productId, quantity } = req.body;
  const orderId = `ORD-${Date.now()}`;
  res.status(201).json({
    id: orderId,
    userId,
    productId,
    quantity: quantity || 1,
    status: 'confirmed',
    total: (PRODUCTS[productId]?.price || 0) * (quantity || 1),
  });
});

app.all('/api/*', (req, res) => {
  res.json({
    method: req.method,
    path: req.path,
    query: req.query,
    body: req.body,
    headers: req.headers,
    timestamp: new Date().toISOString(),
  });
});

const HTTP_PORT = 8080;
const HTTPS_PORT = 8443;

app.listen(HTTP_PORT, () => {
  console.log(`Production service HTTP running on port ${HTTP_PORT}`);
});

if (process.env.TLS_ENABLED === 'true') {
  const certPath = process.env.TLS_CERT || '/etc/nginx/tls/server.crt';
  const keyPath = process.env.TLS_KEY || '/etc/nginx/tls/server.key';

  try {
    const httpsOptions = {
      cert: fs.readFileSync(certPath),
      key: fs.readFileSync(keyPath),
    };

    https.createServer(httpsOptions, app).listen(HTTPS_PORT, () => {
      console.log(`Production service HTTPS running on port ${HTTPS_PORT}`);
    });
  } catch (err) {
    console.log(`TLS certs not found at ${certPath}, HTTPS server not started: ${err.message}`);
  }
}
