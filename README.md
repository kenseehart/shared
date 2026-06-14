# shared

Cross-project assets for the `/home/ken` AI development workspace.

## Contents

| Path | Purpose |
|------|---------|
| `web/chat/` | Zero-build Claude-style chat widget (`agi-chat.js` + `agi-chat.css`) |
| `templates/` | Copy-paste starters for new projects (`AGENTS.md`, Cursor rules) |
| `mcp/` | MCP assets — FastMCP starter + shared GitHub MCP install |
| `AGENTS.md` | Agent onboarding for this repo |

## Usage in a web project

```html
<link rel="stylesheet" href="/path/to/shared/web/chat/agi-chat.css">
<div id="chat"></div>
<script type="module">
  import { AgiChat } from '/path/to/shared/web/chat/agi-chat.js';
  const chat = new AgiChat(document.getElementById('chat'), {
    agentName: 'Claude',
    placeholder: 'Ask anything…',
    onSend: async (text, chat) => {
      chat.appendMessage('user', text);
      chat.setTyping(true);
      const reply = await fetch('/api/chat', { method: 'POST', body: JSON.stringify({ text }) });
      chat.setTyping(false);
      chat.appendMessage('assistant', await reply.text());
    },
  });
</script>
```

Open `web/chat/demo.html` locally to preview.

## Relationship to agi.green

The legacy [agi.green](../agi.green/) framework (Vue + RabbitMQ + Docker) is **not** the shared layer going forward. Salvage its chat UX ideas; use this repo for new work. See `AGENTS.md` for the full verdict.
