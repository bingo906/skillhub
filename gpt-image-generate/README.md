# GPT Image Generate

通过 GPT 兼容的 Responses API 生成或编辑图片的 Codex skill。它会读取本地 Codex 配置或显式传入的 API 参数，调用 `/v1/responses` 并启用 `image_generation` 工具，然后把返回的图片保存到本地文件。

English documentation is available in the second half of this file.

## 中文说明

### 功能

- 文生图：根据文字提示词生成 PNG、JPEG 或 WebP 图片。
- 图生图 / 图片编辑：传入一张或多张参考图，再根据提示词生成编辑后的新图片。
- 自动读取 Codex 配置：默认从本地 Codex 配置中读取 Base URL、API key 和模型。
- 自动兼容流式和 JSON 响应：默认先尝试 stream，未拿到图片时再自动切换到 JSON。
- 直接返回可在 Codex 聊天中展示的 Markdown 图片路径。

### 目录结构

```text
gpt-image-generate/
  SKILL.md
  README.md
  agents/
    openai.yaml
  scripts/
    generate_image.py
```

### 配置方式

脚本按下面的优先级读取配置：

1. 命令行参数：`--base-url`、`--api-key`、`--model`
2. 环境变量：
   - Base URL：`OPENAI_BASE_URL`、`GPT_BASE_URL`、`BASE_URL`
   - API key：`OPENAI_API_KEY`、`GPT_API_KEY`、`API_KEY`
   - Model：`OPENAI_MODEL`、`GPT_MODEL`
3. Codex 配置：
   - Base URL 和 model：`~/.codex/config.toml`
   - API key：`~/.codex/auth.json`

如果使用 Codex 本地配置，通常不需要额外传入 `--base-url` 和 `--api-key`。

不要在日志、README 示例输出或聊天中暴露完整 API key。

### 文生图

在 `gpt-image-generate` 目录中运行：

```bash
python scripts/generate_image.py \
  --prompt "a futuristic city at sunrise, cinematic, highly detailed" \
  --output ./outputs/city.png
```

指定模型或 provider：

```bash
python scripts/generate_image.py \
  --provider any \
  --model gpt-5.5 \
  --prompt "a watercolor illustration of a quiet library" \
  --output ./outputs/library.png
```

指定输出格式：

```bash
python scripts/generate_image.py \
  --prompt "minimal product photo of a smart speaker" \
  --format webp \
  --output ./outputs/speaker.webp
```

### 使用参考图编辑

传入一张参考图：

```bash
python scripts/generate_image.py \
  --prompt "replace the background with snowy mountains, keep the subject unchanged" \
  --image ./refs/person.png \
  --output ./outputs/person-snow.png
```

传入多张参考图：

```bash
python scripts/generate_image.py \
  --prompt "combine the composition of the first image with the visual style of the second image" \
  --image ./refs/composition.png \
  --image ./refs/style.png \
  --output ./outputs/combined.png
```

### 手动指定 API 参数

如果不想读取 Codex 配置，可以显式传参：

```bash
python scripts/generate_image.py \
  --no-codex-config \
  --base-url "https://api.example.com" \
  --api-key "$OPENAI_API_KEY" \
  --model "gpt-5.5" \
  --prompt "a compact electric car in a studio photo" \
  --output ./outputs/car.png
```

也可以使用环境变量：

```bash
export OPENAI_BASE_URL="https://api.example.com"
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-5.5"

python scripts/generate_image.py \
  --prompt "a cozy cabin in the forest at night" \
  --output ./outputs/cabin.png
```

### 响应模式

默认使用 `--request-mode auto`：

- 先请求流式响应。
- 如果流式响应没有返回图片，再自动请求非流式 JSON。

如果某个服务商的流式响应不完整，可以强制使用 JSON：

```bash
python scripts/generate_image.py \
  --request-mode json \
  --prompt "a clean app icon for a calendar product" \
  --output ./outputs/icon.png
```

可选值：

- `auto`：默认值，stream 失败后自动回退到 JSON。
- `stream`：只使用流式响应。
- `json`：只使用非流式 JSON 响应。

### 输出结果

成功时脚本会输出 JSON，例如：

```json
{
  "ok": true,
  "output": "D:\\AICode\\skillhub\\gpt-image-generate\\outputs\\image.png",
  "bytes": 123456,
  "elapsed_seconds": 8.52,
  "base_url": "https://api.example.com",
  "model": "gpt-5.5",
  "response_mode": "json",
  "markdown_image": "![generated image](D:/AICode/skillhub/gpt-image-generate/outputs/image.png)"
}
```

在 Codex 聊天中展示图片时，使用 `markdown_image` 字段，或手动写绝对路径：

```markdown
![generated image](D:/AICode/skillhub/gpt-image-generate/outputs/image.png)
```

### 常见问题

**提示 Base URL is required**

请设置 `OPENAI_BASE_URL` / `GPT_BASE_URL`，传入 `--base-url`，或确认 `~/.codex/config.toml` 中有可用的 provider 配置。

**提示 API key is required**

请设置 `OPENAI_API_KEY` / `GPT_API_KEY`，传入 `--api-key`，或确认 `~/.codex/auth.json` 中有可用密钥。

**提示 No base64 image was found**

说明接口返回成功但脚本没有找到图片数据。可以尝试：

- 使用 `--request-mode json`
- 换一个支持 Responses API `image_generation` 工具的模型
- 检查服务商是否兼容 `/v1/responses`

**参考图路径不存在**

确认 `--image` 后面的路径存在，并且从当前运行目录可以访问。也可以传入绝对路径。

### Codex 中的使用建议

当用户要求生成图片、编辑参考图、调用 `image_generation`、或直接展示保存后的本地图片时，可以使用这个 skill。推荐工作流：

1. 明确输出路径，例如 `./outputs/result.png`。
2. 运行 `scripts/generate_image.py`。
3. 成功后使用脚本输出里的 `markdown_image` 展示图片。
4. 简要报告保存路径和必要的错误信息，不输出密钥。

## English

### Overview

GPT Image Generate is a Codex skill for generating or editing images through a GPT-compatible Responses API. It reads API configuration from local Codex config, environment variables, or explicit CLI arguments, calls `/v1/responses` with the `image_generation` tool enabled, and saves the returned image to disk.

### Features

- Text-to-image generation from a prompt.
- Image editing from one or more reference images.
- PNG, JPEG, and WebP output.
- Automatic Codex config loading.
- Automatic stream-to-JSON fallback in `auto` request mode.
- Markdown image output that can be shown directly in Codex chat.

### Project Layout

```text
gpt-image-generate/
  SKILL.md
  README.md
  agents/
    openai.yaml
  scripts/
    generate_image.py
```

### Configuration

The script resolves configuration in this order:

1. CLI flags: `--base-url`, `--api-key`, `--model`
2. Environment variables:
   - Base URL: `OPENAI_BASE_URL`, `GPT_BASE_URL`, `BASE_URL`
   - API key: `OPENAI_API_KEY`, `GPT_API_KEY`, `API_KEY`
   - Model: `OPENAI_MODEL`, `GPT_MODEL`
3. Codex config:
   - Base URL and model: `~/.codex/config.toml`
   - API key: `~/.codex/auth.json`

If your Codex config is already set up, you usually do not need to pass `--base-url` or `--api-key`.

Never print or share the full API key.

### Generate an Image

Run from the `gpt-image-generate` directory:

```bash
python scripts/generate_image.py \
  --prompt "a futuristic city at sunrise, cinematic, highly detailed" \
  --output ./outputs/city.png
```

Specify a model or provider:

```bash
python scripts/generate_image.py \
  --provider any \
  --model gpt-5.5 \
  --prompt "a watercolor illustration of a quiet library" \
  --output ./outputs/library.png
```

Choose an output format:

```bash
python scripts/generate_image.py \
  --prompt "minimal product photo of a smart speaker" \
  --format webp \
  --output ./outputs/speaker.webp
```

### Edit from Reference Images

Use one reference image:

```bash
python scripts/generate_image.py \
  --prompt "replace the background with snowy mountains, keep the subject unchanged" \
  --image ./refs/person.png \
  --output ./outputs/person-snow.png
```

Use multiple reference images:

```bash
python scripts/generate_image.py \
  --prompt "combine the composition of the first image with the visual style of the second image" \
  --image ./refs/composition.png \
  --image ./refs/style.png \
  --output ./outputs/combined.png
```

### Pass API Settings Explicitly

To avoid reading Codex config, pass all API settings explicitly:

```bash
python scripts/generate_image.py \
  --no-codex-config \
  --base-url "https://api.example.com" \
  --api-key "$OPENAI_API_KEY" \
  --model "gpt-5.5" \
  --prompt "a compact electric car in a studio photo" \
  --output ./outputs/car.png
```

You can also use environment variables:

```bash
export OPENAI_BASE_URL="https://api.example.com"
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-5.5"

python scripts/generate_image.py \
  --prompt "a cozy cabin in the forest at night" \
  --output ./outputs/cabin.png
```

### Request Modes

The default mode is `--request-mode auto`:

- Try streaming first.
- If no image is found in the stream, retry with non-streaming JSON.

If a provider has incomplete streaming support, force JSON mode:

```bash
python scripts/generate_image.py \
  --request-mode json \
  --prompt "a clean app icon for a calendar product" \
  --output ./outputs/icon.png
```

Available values:

- `auto`: default, stream first and fallback to JSON.
- `stream`: streaming response only.
- `json`: non-streaming JSON response only.

### Output

On success, the script prints JSON:

```json
{
  "ok": true,
  "output": "D:\\AICode\\skillhub\\gpt-image-generate\\outputs\\image.png",
  "bytes": 123456,
  "elapsed_seconds": 8.52,
  "base_url": "https://api.example.com",
  "model": "gpt-5.5",
  "response_mode": "json",
  "markdown_image": "![generated image](D:/AICode/skillhub/gpt-image-generate/outputs/image.png)"
}
```

To show the image in Codex chat, use the `markdown_image` value or an absolute Markdown image path:

```markdown
![generated image](D:/AICode/skillhub/gpt-image-generate/outputs/image.png)
```

### Troubleshooting

**Base URL is required**

Set `OPENAI_BASE_URL` / `GPT_BASE_URL`, pass `--base-url`, or confirm that `~/.codex/config.toml` contains a usable provider config.

**API key is required**

Set `OPENAI_API_KEY` / `GPT_API_KEY`, pass `--api-key`, or confirm that `~/.codex/auth.json` contains a usable key.

**No base64 image was found**

The API responded, but the script could not find image data. Try:

- `--request-mode json`
- A model that supports the Responses API `image_generation` tool
- Confirming that your provider supports `/v1/responses`

**Reference image does not exist**

Check the path passed to `--image`. It must exist and be accessible from the current working directory. Absolute paths are also supported.

### Recommended Codex Workflow

Use this skill when the user asks to generate an image, edit an image from references, call `image_generation`, or show a saved local image in Codex chat:

1. Choose an explicit output path, such as `./outputs/result.png`.
2. Run `scripts/generate_image.py`.
3. On success, show the image using the returned `markdown_image` value.
4. Report the saved path and concise errors only. Do not print secrets.
