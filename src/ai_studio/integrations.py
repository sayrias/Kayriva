"""Validated MCP configuration interchange. No command is executed by import."""
from __future__ import annotations

import copy
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def validate_spec(spec: dict, name: str | None = None) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("Her bağlantı bir JSON nesnesi olmalı")
    clean = copy.deepcopy(spec)
    clean["name"] = str(name if name is not None else clean.get("name", "")).strip()
    if not clean["name"] or len(clean["name"]) > 100:
        raise ValueError("Bağlantı adı 1–100 karakter olmalı")
    clean["transport"] = clean.get("transport", "http" if clean.get("url") else "stdio")
    if clean["transport"] == "stdio":
        command, args = clean.get("command"), clean.get("args", [])
        if not isinstance(command, str) or not command.strip() or "\x00" in command:
            raise ValueError("Çalıştırılacak program gerekli; program ve argümanları ayrı gir")
        if not isinstance(args, list) or not all(isinstance(a, str) and "\x00" not in a for a in args):
            raise ValueError("Argümanlar metinlerden oluşan bir JSON dizisi olmalı")
        env = clean.get("env", {})
        if not isinstance(env, dict) or not all(isinstance(k, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) and isinstance(v, str) and "\x00" not in v for k, v in env.items()):
            raise ValueError("Ortam değişkenleri geçerli ad ve metin değerleri içermeli")
        if clean.get("cwd") is not None and not isinstance(clean["cwd"], str):
            raise ValueError("Çalışma klasörü bir yol olmalı")
        clean.update(command=command.strip(), args=args, env=env)
        for key in ("url", "headers", "header_env"):
            clean.pop(key, None)
    elif clean["transport"] == "http":
        url = clean.get("url", "")
        if not isinstance(url, str):
            raise ValueError("HTTP(S) adresi gerekli")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Kimlik bilgisi içermeyen bir HTTP(S) adresi gerekli")
        for key in ("headers", "header_env"):
            values = clean.get(key, {})
            if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) and not any(c in k + v for c in "\r\n\x00") for k, v in values.items()):
                raise ValueError("Başlıklar ad ve metin değerleri içermeli")
        for key in clean.get("header_env", {}).values():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError("Başlık için geçerli bir ortam değişkeni adı gerekli")
        for key in ("command", "args", "env", "cwd"):
            clean.pop(key, None)
    else:
        raise ValueError("Desteklenen bağlantılar: stdio ve HTTP")
    clean["enabled"] = bool(clean.get("enabled", False))
    return clean


def import_configuration(raw: str) -> list[dict]:
    if len(raw.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Yapılandırma 1 MB sınırını aşıyor")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Geçerli bir JSON yapılandırması gerekli") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON içinde mcpServers nesnesi gerekli")
    servers = data.get("mcpServers", data.get("servers"))
    if not isinstance(servers, dict) or not servers or len(servers) > 100:
        raise ValueError("mcpServers 1–100 bağlantı içermeli")
    result = []
    for name, spec in servers.items():
        item = validate_spec(spec, name)
        item["enabled"] = False
        result.append(item)
    return result


def export_configuration(servers: list[dict]) -> str:
    """Export environment references; omit inline credential values."""
    result = {}
    for raw in servers:
        spec = validate_spec(raw)
        name = spec.pop("name")
        for key in ("enabled", "library_id", "installed_version"):
            spec.pop(key, None)
        spec["env"] = {key: value for key, value in spec.get("env", {}).items()
                       if not re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY", key, re.I)}
        spec["headers"] = {key: value for key, value in spec.get("headers", {}).items()
                           if key.lower() not in {"authorization", "cookie", "x-api-key", "proxy-authorization"}}
        for field in ("env", "headers"):
            if not spec[field]:
                spec.pop(field)
        if "url" in spec:
            parsed = urlsplit(spec["url"])
            query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                     if not re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|KEY|AUTH", key, re.I)]
            spec["url"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
        if "args" in spec:
            args, hide_next = [], False
            for arg in spec["args"]:
                if hide_next:
                    args.append("REDACTED")
                    hide_next = False
                elif arg.startswith("-") and re.search(r"token|secret|password|api[-_]?key|authorization", arg, re.I):
                    key, separator, _ = arg.partition("=")
                    args.append(key + "=REDACTED" if separator else key)
                    hide_next = not separator
                else:
                    args.append(arg)
            spec["args"] = args
        result[name] = spec
    return json.dumps({"mcpServers": result}, ensure_ascii=False, indent=2)
