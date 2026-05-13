const http = require("http");
const https = require("https");
const path = require("path");
const fs = require("fs");
const { ExpressPeerServer } = require("peer");
const express = require("express");

const PORT = parseInt(process.env.PORT || "9000", 10);
const ENABLE_HTTPS = (process.env.ENABLE_HTTPS || "").toLowerCase() === "true";
const SSL_KEY_PATH = process.env.SSL_KEY_PATH || path.join(__dirname, "key.pem");
const SSL_CERT_PATH = process.env.SSL_CERT_PATH || path.join(__dirname, "cert.pem");

const rooms = new Map();

function getOrCreateRoom(roomId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, {
      id: roomId,
      hostId: null,
      members: new Set(),
      permissions: {
        whiteboard: true,
        chat: true,
        fileShare: true,
      },
      files: [],
      createdAt: Date.now(),
    });
  }
  return rooms.get(roomId);
}

function serializeRoom(room) {
  return {
    id: room.id,
    hostId: room.hostId,
    members: Array.from(room.members),
    permissions: room.permissions,
    files: room.files,
  };
}

function createServer(app) {
  if (ENABLE_HTTPS) {
    if (!fs.existsSync(SSL_KEY_PATH) || !fs.existsSync(SSL_CERT_PATH)) {
      console.warn(
        "WARN: ENABLE_HTTPS=true 但证书文件不存在，将回退到 HTTP。",
        `期望的证书路径: ${SSL_KEY_PATH}, ${SSL_CERT_PATH}`
      );
      return http.createServer(app);
    }
    const options = {
      key: fs.readFileSync(SSL_KEY_PATH),
      cert: fs.readFileSync(SSL_CERT_PATH),
    };
    return https.createServer(options, app);
  }
  return http.createServer(app);
}

const app = express();
const server = createServer(app);
const protocol = ENABLE_HTTPS ? "https" : "http";

const peerServer = ExpressPeerServer(server, {
  path: "/",
  debug: true,
});

app.use(express.json());
app.use("/peerjs", peerServer);

app.get("/api/room/:id", (req, res) => {
  const room = rooms.get(req.params.id);
  if (!room) {
    return res.status(404).json({ error: "room not found" });
  }
  res.json(serializeRoom(room));
});

const clientPath = path.resolve(__dirname, "..", "client");
app.use(express.static(clientPath));

app.get("/", (_req, res) => {
  const indexPath = path.join(clientPath, "index.html");
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send("index.html not found");
  }
});

peerServer.on("connection", (client) => {
  console.log(`Peer connected: ${client.id}`);
});

peerServer.on("disconnect", (client) => {
  console.log(`Peer disconnected: ${client.id}`);
  rooms.forEach((room) => {
    if (room.members.has(client.id)) {
      room.members.delete(client.id);
      if (room.hostId === client.id) {
        room.hostId = room.members.values().next().value || null;
      }
      if (room.members.size === 0) {
        rooms.delete(room.id);
      }
    }
  });
});

server.listen(PORT, () => {
  console.log(`Server running at ${protocol}://localhost:${PORT}`);
  console.log(`PeerJS signaling at ${protocol}://localhost:${PORT}/peerjs`);
  if (ENABLE_HTTPS) {
    console.log(`Using SSL key: ${SSL_KEY_PATH}`);
    console.log(`Using SSL cert: ${SSL_CERT_PATH}`);
  }
});
