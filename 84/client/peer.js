(function () {
  const SIGNALING_HOST = location.hostname;
  const SIGNALING_PORT = parseInt(location.port || "9000", 10);
  const SIGNALING_PATH = "/peerjs";
  const RECONNECT_DELAY_MS = 1500;

  let peer = null;
  let currentConnection = null;
  let localScreenStream = null;
  let currentCall = null;
  let reconnectTimer = null;
  let sessionMode = null;
  let sessionTarget = null;
  let myId = null;

  const permissions = {
    whiteboard: true,
    chat: true,
    fileShare: true,
  };

  const statusEl = document.getElementById("status");
  const peerIdInput = document.getElementById("peerIdInput");
  const hostBtn = document.getElementById("hostBtn");
  const joinBtn = document.getElementById("joinBtn");
  const screenBtn = document.getElementById("screenBtn");
  const disconnectBtn = document.getElementById("disconnectBtn");
  const screenVideo = document.getElementById("screenVideo");

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function setButtons(state) {
    if (hostBtn) hostBtn.disabled = state === "connected" || state === "incall";
    if (joinBtn) joinBtn.disabled = state === "connected" || state === "incall";
    if (peerIdInput) peerIdInput.disabled = state === "connected" || state === "incall";
    if (screenBtn) screenBtn.disabled = state !== "connected";
    if (disconnectBtn) disconnectBtn.disabled = state === "idle";
  }

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function emitSessionChange() {
    window.dispatchEvent(
      new CustomEvent("session:change", {
        detail: {
          sessionMode,
          sessionTarget,
          myId,
          permissions,
        },
      })
    );
  }

  function emitPermissionChange() {
    window.dispatchEvent(
      new CustomEvent("permissions:change", {
        detail: { permissions: { ...permissions } },
      })
    );
  }

  function setupPeer(id) {
    if (peer) {
      try { peer.destroy(); } catch (e) {}
      peer = null;
    }
    clearReconnectTimer();
    myId = id;
    permissions.whiteboard = true;
    permissions.chat = true;
    permissions.fileShare = true;
    emitSessionChange();
    emitPermissionChange();

    peer = new Peer(id, {
      host: SIGNALING_HOST,
      port: SIGNALING_PORT,
      path: SIGNALING_PATH,
      debug: 1,
    });

    peer.on("open", (pid) => {
      myId = pid;
      setStatus(`已连接信令服务器，你的 ID: ${pid}`);
      setButtons("connected");
      emitSessionChange();
      if (sessionMode === "join" && sessionTarget) {
        initiateConnection(sessionTarget);
      }
    });

    peer.on("connection", (conn) => {
      if (currentConnection) {
        conn.on("open", () => conn.send({ type: "busy" }));
        return;
      }
      attachDataConnection(conn);
    });

    peer.on("call", (call) => {
      call.answer(localScreenStream);
      attachMediaCall(call, true);
    });

    peer.on("error", (err) => {
      console.error(err);
      setStatus(`错误: ${err.type || err.message}`);
    });

    peer.on("disconnected", () => {
      setStatus("与信令服务器断开，正在尝试重连...");
      setButtons("idle");
      scheduleReconnect();
    });

    peer.on("close", () => {
      clearReconnectTimer();
    });
  }

  function scheduleReconnect() {
    clearReconnectTimer();
    if (!sessionMode) return;
    reconnectTimer = setTimeout(() => {
      if (!sessionMode) return;
      setStatus("正在重新连接信令服务器...");
      if (sessionMode === "host") {
        setupPeer(sessionTarget);
      } else if (sessionMode === "join") {
        const localId =
          "guest-" +
          sessionTarget +
          "-" +
          Math.random().toString(36).slice(2, 8);
        setupPeer(localId);
      }
    }, RECONNECT_DELAY_MS);
  }

  function handleIncomingMessage(msg) {
    if (!msg) return;
    switch (msg.type) {
      case "whiteboard":
        window.dispatchEvent(
          new CustomEvent("whiteboard:remote", { detail: msg.payload })
        );
        break;
      case "chat":
        window.dispatchEvent(
          new CustomEvent("chat:incoming", { detail: msg.payload })
        );
        break;
      case "file":
        window.dispatchEvent(
          new CustomEvent("file:incoming", { detail: msg.payload })
        );
        break;
      case "permissions":
        if (msg.payload && msg.payload.permissions) {
          Object.assign(permissions, msg.payload.permissions);
          emitPermissionChange();
        }
        break;
      case "request-permissions":
        if (sessionMode === "host" && currentConnection) {
          currentConnection.send({
            type: "permissions",
            payload: { permissions: { ...permissions } },
          });
        }
        break;
      default:
        break;
    }
  }

  function attachDataConnection(conn) {
    currentConnection = conn;
    setStatus("数据通道已连接");
    setButtons("incall");

    if (sessionMode === "host") {
      conn.send({
        type: "permissions",
        payload: { permissions: { ...permissions } },
      });
    } else {
      conn.send({ type: "request-permissions" });
    }

    conn.on("data", (data) => {
      if (!data) return;
      if (data.type === "busy") {
        setStatus("对方已在通话中");
        cleanup();
        return;
      }
      handleIncomingMessage(data);
    });

    conn.on("close", () => {
      setStatus("数据通道已关闭");
      cleanupCall();
    });

    conn.on("error", (err) => {
      console.error(err);
      cleanupCall();
    });

    window.dispatchEvent(new CustomEvent("connection:open"));
  }

  function attachMediaCall(call, incoming) {
    currentCall = call;
    setButtons("incall");
    if (!incoming) {
      setStatus("正在呼叫对方...");
    }
    call.on("stream", (remoteStream) => {
      screenVideo.srcObject = remoteStream;
      setStatus("已收到对方屏幕流");
    });
    call.on("close", () => {
      setStatus("媒体流已关闭");
      cleanupCall();
    });
    call.on("error", (err) => {
      console.error(err);
      cleanupCall();
    });
  }

  function initiateConnection(targetId) {
    if (!peer || peer.destroyed || peer.disconnected) return;
    const conn = peer.connect(targetId, { reliable: true });
    conn.on("open", () => {
      attachDataConnection(conn);
    });
    conn.on("error", (err) => {
      console.error(err);
      setStatus("连接失败");
    });
  }

  async function startScreenShare() {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });
      localScreenStream = stream;
      screenVideo.srcObject = stream;
      setStatus("本地屏幕已共享");
      if (currentConnection && !currentCall) {
        const call = peer.call(currentConnection.peer, stream);
        attachMediaCall(call, false);
      }
      stream.getVideoTracks()[0].addEventListener("ended", stopScreenShare);
    } catch (err) {
      console.error(err);
      setStatus("屏幕共享失败或被取消");
    }
  }

  function stopScreenShare() {
    if (localScreenStream) {
      localScreenStream.getTracks().forEach((t) => t.stop());
      localScreenStream = null;
    }
    if (screenVideo) screenVideo.srcObject = null;
    if (currentCall) {
      try { currentCall.close(); } catch (e) {}
      currentCall = null;
    }
  }

  function cleanupCall() {
    currentConnection = null;
    currentCall = null;
    if (peer && !peer.destroyed) {
      setButtons("connected");
      setStatus("已断开通话，等待新的连接");
    } else {
      setButtons("idle");
    }
    window.dispatchEvent(new CustomEvent("connection:close"));
  }

  function cleanup() {
    clearReconnectTimer();
    sessionMode = null;
    sessionTarget = null;
    myId = null;
    stopScreenShare();
    if (currentConnection) {
      try { currentConnection.close(); } catch (e) {}
      currentConnection = null;
    }
    if (peer) {
      try { peer.destroy(); } catch (e) {}
      peer = null;
    }
    setButtons("idle");
    setStatus("已断开");
    emitSessionChange();
    window.dispatchEvent(new CustomEvent("connection:close"));
  }

  window.rtcSession = {
    getMode: () => sessionMode,
    getTarget: () => sessionTarget,
    getMyId: () => myId,
    isHost: () => sessionMode === "host",
    getPermissions: () => ({ ...permissions }),
    setPermissions: (next) => {
      if (sessionMode !== "host") return;
      Object.assign(permissions, next);
      emitPermissionChange();
      if (currentConnection && currentConnection.open) {
        currentConnection.send({
          type: "permissions",
          payload: { permissions: { ...permissions } },
        });
      }
    },
    send: (type, payload) => {
      if (!currentConnection || !currentConnection.open) return false;
      currentConnection.send({ type, payload });
      return true;
    },
  };

  if (hostBtn) {
    hostBtn.addEventListener("click", () => {
      const id = (peerIdInput ? peerIdInput.value : "").trim();
      if (!id) {
        setStatus("请输入房间 ID");
        return;
      }
      cleanup();
      sessionMode = "host";
      sessionTarget = id;
      setupPeer(id);
    });
  }

  if (joinBtn) {
    joinBtn.addEventListener("click", () => {
      const targetId = (peerIdInput ? peerIdInput.value : "").trim();
      if (!targetId) {
        setStatus("请输入房间 ID");
        return;
      }
      cleanup();
      sessionMode = "join";
      sessionTarget = targetId;
      const localId =
        "guest-" +
        targetId +
        "-" +
        Math.random().toString(36).slice(2, 8);
      setupPeer(localId);
    });
  }

  if (screenBtn) {
    screenBtn.addEventListener("click", () => {
      startScreenShare();
    });
  }

  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", () => {
      cleanup();
    });
  }

  setButtons("idle");
})();
