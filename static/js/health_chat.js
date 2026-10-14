(() => {
  const messagesEl = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const button = document.getElementById("chat-send");
  const counter = document.getElementById("chat-counter");

  if (!messagesEl || !form || !input || !button || !counter) return;

  const csrfInput = form.querySelector('[name="csrfmiddlewaretoken"]');
  const csrf = csrfInput ? csrfInput.value : "";
  const history = [];

  function addMessage(role, text) {
    const row = document.createElement("div");
    row.className = `hc-message hc-message-${role}`;

    const avatar = document.createElement("span");
    avatar.className = `hc-message-avatar hc-message-avatar-${role}`;
    const icon = document.createElement("i");
    icon.className = role === "user" ? "fa-solid fa-user" : "fa-solid fa-heart-pulse";
    avatar.appendChild(icon);

    const bubble = document.createElement("div");
    bubble.className = `hc-bubble hc-bubble-${role}`;
    const label = document.createElement("span");
    label.className = "hc-bubble-label";
    label.textContent = role === "user" ? "You" : "MeCare Assistant";
    const body = document.createElement("div");
    body.className = "hc-bubble-body";
    body.textContent = text;
    bubble.append(label, body);
    row.append(avatar, bubble);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return body;
  }

  addMessage(
    "assistant",
    "Namaste! Aap Hindi ya English mein general health information ya hospital departments ke baare mein pooch sakte hain.\n\nHello! Ask me in Hindi or English about general health information or hospital departments."
  );

  input.addEventListener("input", () => {
    button.disabled = !input.value.trim() || button.dataset.busy === "true";
    counter.textContent = `${input.value.length} / 1200`;
  });

  document.querySelectorAll(".hc-prompt").forEach((prompt) => {
    prompt.addEventListener("click", () => {
      input.value = prompt.dataset.prompt || "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      input.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || button.dataset.busy === "true") return;

    history.push({ role: "user", content: text });
    addMessage("user", text);
    input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    button.dataset.busy = "true";
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
    const pending = addMessage("assistant", "Soch raha hoon... / Thinking...");

    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ messages: history.slice(-10) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
      pending.textContent = data.reply;
      history.push({ role: "assistant", content: data.reply });
    } catch (error) {
      pending.textContent = error.message || "Could not reach the assistant. Please try again.";
      pending.classList.add("hc-error-message");
      history.pop();
    } finally {
      button.dataset.busy = "false";
      button.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
      button.disabled = !input.value.trim();
      input.focus();
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
})();
