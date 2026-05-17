# SkillHub

一个用于整理和分发 AI 工具 Skills 的仓库。这里会持续收集可直接安装到 Codex、OpenClaw、Hermes 等工具中的本地 Skill。

This repository collects local Skills for AI coding tools such as Codex, OpenClaw, and Hermes. Each Skill is designed to be easy to install, inspect, and reuse.

---

## Skills / 技能导航

| Skill | Description | 中文说明 | Guide |
| --- | --- | --- | --- |
| [`gpt-image-generate`](./gpt-image-generate/) | Generate or edit images through a GPT-compatible Responses API with the `image_generation` tool. | 通过兼容 GPT 的 Responses API 调用图片生成工具，一句话生成或编辑图片。 | [README](./gpt-image-generate/README.md) |

---

## Install / 安装方式

For most users, download the packaged Skill from [`zip/`](./zip/), unzip it locally, then move the extracted Skill folder into your tool's skills directory.

对大多数用户来说，推荐先到 [`zip/`](./zip/) 目录下载对应 Skill 压缩包，解压后再把 Skill 文件夹放到对应工具的 skills 目录下。

Steps:

1. Download `gpt-image-generate.zip` from [`zip/`](./zip/)
2. Unzip it locally
3. Move the extracted `gpt-image-generate` folder into your skills directory
4. Restart Codex, OpenClaw, or Hermes

安装步骤：

1. 从 [`zip/`](./zip/) 下载 `gpt-image-generate.zip`
2. 在本地解压
3. 把解压出来的 `gpt-image-generate` 文件夹移动到 skills 目录
4. 重启 Codex、OpenClaw 或 Hermes

Codex on Windows usually uses:

```text
C:\Users\你的用户名\.codex\skills
```

Linux / macOS usually uses:

```text
~/.codex/skills/
```

For OpenClaw or Hermes, place the Skill in the directory recognized by that tool, then restart the app or plugin.

OpenClaw 或 Hermes 用户，把 Skill 放到对应工具识别的 skills / plugins 目录后，重启工具即可。

---

## Current Highlight / 当前推荐

### `gpt-image-generate`

Use it in your AI tool prompt:

```text
$gpt-image-generate 使用该技能生图：一张未来城市夜景，霓虹灯，雨天，电影海报风格
```

Requirements:

- A provider that supports `/v1/responses`
- Support for the `image_generation` tool
- Valid Base URL and API Key configuration

核心要求：

- 服务端支持 `/v1/responses`
- 服务端支持 `image_generation` 工具
- 已正确配置 Base URL 和 API Key

Read more: [gpt-image-generate/README.md](./gpt-image-generate/README.md)
