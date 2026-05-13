(function () {
  const chatInput = document.getElementById("chatInput");
  const chatSendBtn = document.getElementById("chatSendBtn");
  const chatMessages = document.getElementById("chatMessages");

  const messages = [];

  function escapeHtml(text) {
    return (text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function render() {
    if (!chatMessages) return;
    chatMessages.innerHTML = messages
      .map((m) => {
        const mine = m.role === "me";
        const header = mine
          ? "<span style=\"color:#38bdf8;font-weight:600;\">我</span>"
          : "<span style=\"color:#22c55e;font-weight:600;\">对方</span>";
        return `<div style="margin:6px 0;font-size:13px;">${header} ${escapeHtml(
          m.text
        )}</div>`;
      })
      .join("");
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function sendMessage() {
    if (!chatInput) return;
    const text = chatInput.value.trim();
    if (!text) return;
    if (!window.rtcSession) return;
    const perms = window.rtcSession.getPermissions();
    if (!perms.chat) {
      alert("主持人未开启聊天权限");
      return;
    }
    if (!window.rtcSession.send("chat", { from: "me", text })) {
      alert("当前未建立连接");
      return;
    }
    messages.push({ role: "me", text });
    chatInput.value = "";
    render();
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  if (chatSendBtn) {
    chatSendBtn.addEventListener("click", sendMessage);
  }

  window.addEventListener("chat:incoming", (e) => {
    const payload = e.detail;
    if (!payload || !payload.text) return;
    messages.push({ role: "other", text: payload.text });
    render();
  });

  window.addEventListener("connection:close", () => {
    messages.length = 0;
    render();
  });

  render();
})();
