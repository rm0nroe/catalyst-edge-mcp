const OFFER_VERSION = "hosted-pro-29-v1-2026-08-04-live";
const params = new URLSearchParams(location.search);
const qa = params.get("qa") === "1";
const source = String(params.get("utm_source") || document.referrer || "direct").slice(0, 64);
const visitorId = localStorage.getItem("catalyst-visitor") || crypto.randomUUID();
localStorage.setItem("catalyst-visitor", visitorId);

async function post(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, offerVersion: OFFER_VERSION, visitorId, source, qa }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function event(name) {
  return post("/api/event", { event: name });
}

function track(name) {
  event(name).catch(() => {});
}

if (location.pathname === "/confirm") {
  const section = document.querySelector("#confirmation");
  document.querySelector("header").hidden = true;
  document.querySelector("main").hidden = true;
  document.querySelector("footer").hidden = true;
  section.hidden = false;
  fetch(`/api/confirm?token=${encodeURIComponent(params.get("token") || "")}`)
    .then(async (response) => ({ ok: response.ok, body: await response.json() }))
    .then(({ ok, body }) => {
      document.querySelector("#confirmation-title").textContent = ok ? "Interest confirmed." : "Link not confirmed.";
      document.querySelector("#confirmation-message").textContent = ok
        ? "Your verified response is recorded for this exact $29/month offer. No payment was taken."
        : body.error;
    })
    .catch(() => {
      document.querySelector("#confirmation-title").textContent = "Confirmation unavailable.";
      document.querySelector("#confirmation-message").textContent = "Please try the link again later.";
    });
} else {
  track("offer_exposure");
}

document.querySelectorAll("[data-install]").forEach((link) => link.addEventListener("click", () => track("install_click")));

const organization = document.querySelector("#sec-organization");
const secEmail = document.querySelector("#sec-email");
const codexCommand = document.querySelector("#codex-command");
const copyCommand = document.querySelector("[data-copy='codex-command']");

function shellQuote(value) {
  return `'${value.replaceAll("'", `'"'"'`)}'`;
}

function updateInstallCommand() {
  const ready = organization.value.trim() && secEmail.value && secEmail.checkValidity();
  copyCommand.disabled = !ready;
  copyCommand.textContent = ready ? "Copy command" : "Enter SEC identity to copy";
  codexCommand.textContent = ready
    ? `codex mcp add catalyst-edge \\\n  --env ${shellQuote(`CATALYST_EDGE_SEC_USER_AGENT=${organization.value.trim()} ${secEmail.value}`)} \\\n  -- uvx --from 'catalyst-edge-mcp==0.1.3' catalyst-edge-mcp`
    : "Enter your organization and monitored email to generate the command.";
}

[organization, secEmail].forEach((input) => input?.addEventListener("input", updateInstallCommand));

document.querySelectorAll("[data-copy]").forEach((button) => button.addEventListener("click", async () => {
  await navigator.clipboard.writeText(document.querySelector(`#${button.dataset.copy}`).textContent);
  button.textContent = "Copied";
  track("install_click");
}));

document.querySelector("#activation-button")?.addEventListener("click", async (eventObject) => {
  const button = eventObject.currentTarget;
  const status = document.querySelector("#activation-status");
  button.disabled = true;
  try {
    await event("activation_report");
    status.textContent = "Successful-install report recorded for this browser.";
    button.textContent = "Activation reported";
  } catch {
    status.textContent = "Could not record the report. Please try again.";
    button.disabled = false;
  }
});

document.querySelector("#intent-form")?.addEventListener("submit", async (eventObject) => {
  eventObject.preventDefault();
  const form = eventObject.currentTarget;
  const status = document.querySelector("#intent-status");
  if (!form.reportValidity()) return;
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  status.textContent = "Sending confirmation…";
  const data = new FormData(form);
  try {
    const result = await post("/api/intent", {
      email: data.get("email"),
      client: data.get("client"),
      definitelyPay: data.get("definitelyPay") === "on",
      privacyConsent: data.get("privacyConsent") === "on",
      company: data.get("company"),
    });
    status.textContent = result.alreadyConfirmed
      ? "This email is already confirmed for the current offer."
      : "Check your email and click the one-time confirmation link within 24 hours.";
    form.reset();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
});
