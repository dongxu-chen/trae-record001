(function () {
  const MAX_CHUNK_SIZE = 16 * 1024;

  const fileInput = document.getElementById("fileInput");
  const fileListEl = document.getElementById("fileList");

  const incomingSessions = new Map();
  const outgoingSessions = new Map();
  let idCounter = 0;

  function nextId() {
    idCounter += 1;
    return idCounter;
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  }

  function renderFiles() {
    if (!fileListEl) return;
    const html = [];
    incomingSessions.forEach((session, id) => {
      const progress = session.done
        ? "完成"
        : `${Math.min(100, Math.floor((session.received / session.size) * 100))}%`;
      html.push(
        `<div style="padding:8px 10px;border-radius:8px;background:#1e293b;margin-top:6px;font-size:13px;">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
            <div style="min-width:0;">
              <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${session.name}</div>
              <div style="color:#94a3b8;font-size:12px;">来自对方 · ${formatSize(session.size)} · ${progress}</div>
            </div>
            ${
              session.done && session.blob
                ? `<a style="color:#38bdf8;text-decoration:none;" href="${URL.createObjectURL(
                    session.blob
                  )}" download="${session.name}">下载</a>`
                : ""
            }
          </div>
        </div>`
      );
    });
    fileListEl.innerHTML = html.join("");
  }

  function sendFile(file) {
    if (!window.rtcSession) return;
    const perms = window.rtcSession.getPermissions();
    if (!perms.fileShare) {
      alert("主持人未开启文件共享权限");
      return;
    }
    const id = nextId();
    const session = {
      id,
      name: file.name,
      size: file.size,
      offset: 0,
      file,
    };
    outgoingSessions.set(id, session);
    window.rtcSession.send("file", {
      type: "start",
      id,
      name: file.name,
      size: file.size,
    });
    setTimeout(() => continueOutgoing(id), 0);
  }

  function continueOutgoing(id) {
    const session = outgoingSessions.get(id);
    if (!session) return;
    const reader = new FileReader();
    const chunk = session.file.slice(
      session.offset,
      session.offset + MAX_CHUNK_SIZE
    );
    reader.onload = () => {
      if (!window.rtcSession) return;
      const ok = window.rtcSession.send("file", {
        type: "chunk",
        id,
        offset: session.offset,
        data: reader.result,
      });
      if (!ok) return;
      session.offset += chunk.size;
      if (session.offset >= session.size) {
        outgoingSessions.delete(id);
        window.rtcSession.send("file", {
          type: "end",
          id,
        });
      } else {
        setTimeout(() => continueOutgoing(id), 0);
      }
    };
    reader.onerror = () => {
      outgoingSessions.delete(id);
    };
    reader.readAsArrayBuffer(chunk);
  }

  function handleRemoteFileMessage(payload) {
    if (!payload) return;
    if (payload.type === "start") {
      const perms = window.rtcSession
        ? window.rtcSession.getPermissions()
        : { fileShare: false };
      if (!perms.fileShare) return;
      incomingSessions.set(payload.id, {
        id: payload.id,
        name: payload.name,
        size: payload.size,
        received: 0,
        chunks: [],
        done: false,
        blob: null,
      });
      renderFiles();
    } else if (payload.type === "chunk") {
      const session = incomingSessions.get(payload.id);
      if (!session) return;
      session.chunks.push(payload.data);
      session.received += payload.data.byteLength;
      renderFiles();
    } else if (payload.type === "end") {
      const session = incomingSessions.get(payload.id);
      if (!session) return;
      session.done = true;
      session.blob = new Blob(session.chunks);
      session.chunks = [];
      renderFiles();
    }
  }

  window.addEventListener("file:incoming", (e) => {
    const payload = e.detail;
    if (!payload) return;
    if (payload.type === "ack" && outgoingSessions.has(payload.id)) {
      continueOutgoing(payload.id);
    } else {
      handleRemoteFileMessage(payload);
    }
  });

  window.addEventListener("connection:open", () => {
    if (!window.rtcSession) return;
    outgoingSessions.forEach((session) => {
      window.rtcSession.send("file", {
        type: "start",
        id: session.id,
        name: session.name,
        size: session.size,
      });
    });
  });

  window.addEventListener("connection:close", () => {
    incomingSessions.clear();
    outgoingSessions.clear();
    renderFiles();
  });

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      for (let i = 0; i < files.length; i++) {
        sendFile(files[i]);
      }
      fileInput.value = "";
    });
  }

  renderFiles();
})();
