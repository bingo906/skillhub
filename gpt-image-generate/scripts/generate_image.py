#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL_ENV = ("OPENAI_BASE_URL", "GPT_BASE_URL", "BASE_URL")
API_KEY_ENV = ("OPENAI_API_KEY", "GPT_API_KEY", "API_KEY")
MODEL_ENV = ("OPENAI_MODEL", "GPT_MODEL")

IMAGE_PREFIXES = ("iVBOR", "/9j/", "UklGR", "R0lGOD", "Qk")
PREFERRED_IMAGE_KEYS = ("result", "b64_json", "image_base64", "base64", "data", "image")

SYSTEM_PROMPT = (
    "You are an image generation assistant. When the user asks for an image, "
    "you must call the image_generation tool to generate the image. Do not "
    "describe the image in text. Return the generated image directly."
)
EDIT_PROMPT_PREFIX = (
    "Please edit or transform the provided reference image(s) according to this "
    "request, and directly generate the modified new image. Request: "
)


def first_value(names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def normalize_base_url(value):
    if not value:
        raise ValueError("Base URL is required. Set OPENAI_BASE_URL/GPT_BASE_URL or pass --base-url.")
    value = value.strip().rstrip("/")
    if not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError("Base URL must start with http:// or https://")
    if value.endswith("/v1"):
        value = value[:-3]
    return value


def default_codex_home():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def load_toml(path):
    try:
        import tomllib

        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_codex_config(codex_home, provider_name=None):
    codex_home = Path(codex_home).expanduser()
    config_path = codex_home / "config.toml"
    auth_path = codex_home / "auth.json"
    result = {}

    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8", errors="replace")
        parsed = load_toml(config_path)
        if parsed:
            result["model"] = parsed.get("model")
            provider = provider_name or parsed.get("model_provider")
            providers = parsed.get("model_providers") or {}
            provider_cfg = providers.get(provider) if provider else None
            if isinstance(provider_cfg, dict):
                result["base_url"] = provider_cfg.get("base_url")
                result["provider"] = provider
        else:
            model_match = re.search(r'(?m)^model\s*=\s*"([^"]+)"', raw)
            provider_match = re.search(r'(?m)^model_provider\s*=\s*"([^"]+)"', raw)
            provider = provider_name or (provider_match.group(1) if provider_match else None)
            if model_match:
                result["model"] = model_match.group(1)
            if provider:
                pattern = r"(?s)\[model_providers\." + re.escape(provider) + r'\].*?base_url\s*=\s*"([^"]+)"'
                base_match = re.search(pattern, raw)
                if base_match:
                    result["base_url"] = base_match.group(1)
                    result["provider"] = provider

    if auth_path.exists():
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            result["api_key"] = auth.get("OPENAI_API_KEY") or auth.get("api_key")
        except Exception:
            pass

    return result


def image_to_data_url(path):
    image_path = Path(path)
    if not image_path.exists():
        raise ValueError(f"Reference image does not exist: {image_path}")
    data = image_path.read_bytes()
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_payload(args, *, stream):
    prompt = args.prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required.")

    tool = {"type": "image_generation", "output_format": args.format}

    if args.image:
        content = [{"type": "input_image", "image_url": image_to_data_url(image_path)} for image_path in args.image]
        content.append({"type": "input_text", "text": EDIT_PROMPT_PREFIX + prompt})
        return {
            "model": args.model,
            "input": [{"role": "user", "content": content}],
            "tools": [tool],
            "stream": stream,
        }

    return {
        "model": args.model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Generate an image from this description: " + prompt},
        ],
        "tools": [tool],
        "stream": stream,
    }


def looks_like_base64_image(value):
    if not isinstance(value, str):
        return False
    if value.startswith("data:image/"):
        return True
    if len(value) < 1000:
        return False
    return value.startswith(IMAGE_PREFIXES)


def as_image_bytes(value):
    if value.startswith("data:image/"):
        _, encoded = value.split(",", 1)
    else:
        encoded = value
    return base64.b64decode(encoded)


def extract_image_base64(obj):
    if obj is None:
        return None
    if isinstance(obj, list):
        for item in obj:
            found = extract_image_base64(item)
            if found:
                return found
        return None
    if isinstance(obj, dict):
        for key in PREFERRED_IMAGE_KEYS:
            value = obj.get(key)
            if looks_like_base64_image(value):
                return value
        for value in obj.values():
            found = extract_image_base64(value)
            if found:
                return found
        return None
    if looks_like_base64_image(obj):
        return obj
    return None


def iter_sse_events(response):
    buffer = ""
    event_name = None
    data_lines = []

    def emit():
        if not data_lines:
            return None
        return event_name, "\n".join(data_lines)

    while True:
        chunk = response.read(8192)
        if not chunk:
            item = emit()
            if item:
                yield item
            break

        buffer += chunk.decode("utf-8", errors="replace")
        lines = buffer.splitlines(keepends=True)
        if lines and not (lines[-1].endswith("\n") or lines[-1].endswith("\r")):
            buffer = lines.pop()
        else:
            buffer = ""

        for raw_line in lines:
            line = raw_line.rstrip("\r\n")
            if not line:
                item = emit()
                if item:
                    yield item
                event_name = None
                data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())


def iter_sse_json(response):
    for _event_name, data in iter_sse_events(response):
        if data == "[DONE]":
            return
        if not data:
            continue
        try:
            yield json.loads(data)
        except json.JSONDecodeError:
            continue


def request_headers(args, *, stream):
    headers = {
        "Authorization": "Bearer " + args.api_key,
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        # Some Codex-compatible routers expect these browser-client hints.
        "chatgpt-account-id": "",
        "version": "0.122.0",
        "originator": "codex_cli_rs",
        "session_id": "gpt-image-generate-" + str(int(time.time() * 1000)),
    }
    return headers


def post_response(args, *, stream):
    payload = build_payload(args, stream=stream)
    url = args.base_url + "/v1/responses"
    body = json.dumps(payload).encode("utf-8")
    headers = request_headers(args, stream=stream)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return urllib.request.urlopen(req, timeout=args.timeout)


def find_image_in_stream(args, started):
    with post_response(args, stream=True) as response:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" not in content_type:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            found = extract_image_base64(data)
            if found:
                return as_image_bytes(found), time.time() - started, "stream-json"
            return None

        for data in iter_sse_json(response):
            found = extract_image_base64(data)
            if found:
                return as_image_bytes(found), time.time() - started, "stream"

    return None


def find_image_in_json(args, started):
    with post_response(args, stream=False) as response:
        raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        found = extract_image_base64(data)
        if found:
            return as_image_bytes(found), time.time() - started, "json"
    return None


def request_image(args):
    started = time.time()

    if args.request_mode in ("stream", "auto"):
        stream_result = find_image_in_stream(args, started)
        if stream_result:
            return stream_result
        if args.request_mode == "stream":
            raise RuntimeError("No base64 image was found in the streamed API response.")

    json_result = find_image_in_json(args, started)
    if json_result:
        return json_result

    raise RuntimeError("No base64 image was found in the API response.")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate or edit an image through a GPT-compatible Responses API.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--codex-home", default=str(default_codex_home()))
    parser.add_argument("--provider", default=None, help="Codex model provider name from config.toml.")
    parser.add_argument("--no-codex-config", action="store_true", help="Do not read ~/.codex/config.toml or auth.json.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image", action="append", help="Reference image path. Can be repeated.")
    parser.add_argument("--output", default="generated-image.png")
    parser.add_argument("--format", choices=("png", "jpeg", "webp"), default="png")
    parser.add_argument("--request-mode", choices=("auto", "stream", "json"), default="auto")
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        codex_cfg = {} if args.no_codex_config else read_codex_config(args.codex_home, args.provider)
        args.base_url = args.base_url or first_value(BASE_URL_ENV) or codex_cfg.get("base_url")
        args.api_key = args.api_key or first_value(API_KEY_ENV) or codex_cfg.get("api_key")
        args.model = args.model or first_value(MODEL_ENV) or codex_cfg.get("model") or "gpt-5.5"
        args.base_url = normalize_base_url(args.base_url)
        if not args.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY/GPT_API_KEY, pass --api-key, or keep it in Codex auth.json.")

        image_bytes, elapsed, response_mode = request_image(args)
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image_bytes)
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": str(output),
                    "bytes": len(image_bytes),
                    "elapsed_seconds": round(elapsed, 2),
                    "base_url": args.base_url,
                    "model": args.model,
                    "response_mode": response_mode,
                    "markdown_image": f"![generated image]({str(output).replace(os.sep, '/')})",
                },
                ensure_ascii=False,
            )
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        print(json.dumps({"ok": False, "status": exc.code, "error": detail}, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
