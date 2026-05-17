---
name: gpt-image-generate
description: Generate or edit images through a GPT-compatible Responses API using the current Codex Base URL and API key from the local Codex config or explicit environment/config. Use when the user asks Codex to use gpt-image-generate, generate an image, edit an image from references, call image_generation, or show a saved local image directly in Codex chat.
---

# GPT Image Generate

Use the bundled script to call a GPT-compatible `/v1/responses` endpoint with the `image_generation` tool enabled, then save the returned image to disk.

The request shape matches the companion local image tool implementation:

- Text-to-image: send a system instruction plus a user prompt, with `tools: [{ "type": "image_generation", "output_format": "png" }]`.
- Image-to-image: send one or more `{ "type": "input_image", "image_url": "data:image/..." }` items followed by one `{ "type": "input_text" }` edit request.
- The script searches returned JSON or streamed SSE events recursively for base64 image payloads, especially `result`.
- In `--request-mode auto`, the script tries streaming first and automatically retries non-streaming JSON if the stream ends without an image.

## Configuration

Resolve credentials in this order:

1. Explicit CLI flags: `--base-url`, `--api-key`, `--model`
2. Environment variables:
   - Base URL: `OPENAI_BASE_URL`, `GPT_BASE_URL`, `BASE_URL`
   - API key: `OPENAI_API_KEY`, `GPT_API_KEY`, `API_KEY`
   - Model: `OPENAI_MODEL`, `GPT_MODEL`
3. Codex config:
   - Base URL and model from `../config.toml`
   - API key from `../auth.json`

Do not print the full API key. If showing configuration, redact it.

## Generate An Image

Run from this skill directory or use the absolute script path:

```bash
python scripts/generate_image.py --prompt "the end of the universe, cinematic deep space" --output ./outputs/image.png
```

The script reads the current Codex config automatically, so flags are only needed to override defaults:

```bash
python scripts/generate_image.py --provider any --model gpt-5.5 --prompt "..." --output ./outputs/image.png
```

## Edit From Reference Images

For image-to-image generation, provide one or more references:

```bash
python scripts/generate_image.py --prompt "replace the background with snowy mountains" --image ./refs/ref.png --output ./outputs/edited.png
```

Multiple references are supported:

```bash
python scripts/generate_image.py --prompt "combine the composition of the first image with the style of the second" --image ./refs/a.png --image ./refs/b.png --output ./outputs/combined.png
```

If a provider's streaming response is incomplete, force JSON mode:

```bash
python scripts/generate_image.py --request-mode json --prompt "..." --output ./outputs/image.png
```

## Show Images In Codex Chat

After generation, show the image directly in the conversation with an absolute local Markdown image path:

```markdown
![image](./outputs/image.png)
```

Use forward slashes in the Markdown path for reliable rendering. Also report the saved file path as plain text.

## Workflow

1. Use `scripts/generate_image.py` with an explicit output path.
2. Let the script auto-load Codex config unless the user provides overrides.
3. On success, include the `markdown_image` value from the script output or manually emit `![image](absolute/path.png)`.
4. Report API errors concisely. Never print secrets.

## Notes

- The upstream API must support the Responses API and `tools: [{ "type": "image_generation" }]`.
- The script sends compatibility headers used by the local browser tool: `chatgpt-account-id`, `version`, `originator`, and `session_id`.
- The script parses Server-Sent Events and JSON responses, recursively searching for base64 image payloads in common fields such as `result`, `b64_json`, `image_base64`, `base64`, and `data`.
- Browser CORS is irrelevant here because the script runs locally from Codex/terminal.
