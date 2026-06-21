# Web assets

Static components shared across sites. No build step.

## Chat widget

| File | Description |
|------|-------------|
| `chat/agi-chat.css` | Claude-inspired theme |
| `chat/agi-chat.js` | `AgiChat` ES module |
| `chat/demo.html` | Local preview |

Preview:

```bash
cd /home/ken/ws/shared/web/chat && python3 -m http.server 8766
# open http://127.0.0.1:8766/demo.html
```

See **`/home/ken/ws/shared/AGENTS.md`** for integration examples.
