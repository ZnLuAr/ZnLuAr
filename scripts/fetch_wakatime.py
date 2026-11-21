#!/usr/bin/env python3
"""Fetch WakaTime coding stats into the persistent hero carousel snapshot."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hero.wakatime import (  # noqa: E402
    EXCLUDED_LANGUAGE_NAMES,
    MAX_EDITORS,
    MAX_LANGUAGES,
    MAX_OPERATING_SYSTEMS,
    RANGE_DAYS,
    WAKATIME_PATH,
    validate_wakatime,
)
from hero.scene import write_json  # noqa: E402

ROOT = SCRIPTS_DIR.parent
API_STATS_URL = "https://wakatime.com/api/v1/users/current/stats/"
DEFAULT_TOKEN_PATH = ROOT / "_wakatime_token.local"


def format_duration(seconds):
    minutes = int(round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} hrs {minutes} mins"


def load_token(token_path):
    """Read the OAuth token from a gitignored local file or the environment."""
    token = os.environ.get("WAKATIME_OAUTH_TOKEN", "").strip()
    source = "environment variable WAKATIME_OAUTH_TOKEN"
    if not token and token_path.is_file():
        token = token_path.read_text(encoding="utf-8").strip()
        source = str(token_path.relative_to(ROOT))
    if not token:
        raise SystemExit(
            "未找到 WakaTime OAuth token：请参考 _wakatime_token.local.example"
            " 复制为 _wakatime_token.local（仓库根目录，已在 .gitignore 中），"
            "或设置环境变量 WAKATIME_OAUTH_TOKEN。"
            "注意插件 API key 是 write-only，读取统计需要 https://wakatime.com/oauth 的 OAuth token。"
        )
    if token.startswith("waka_sec_"):
        raise SystemExit(
            f"该值看起来是账号 Secret API key（来自 {source}），不能读取统计（实测返回 401）；"
            "请改用 OAuth access token（waka_tok_ 前缀），"
            "可通过 https://wakatime.com/oauth 的个人 token 或 OAuth app 授权流程获取。"
        )
    return token


def fetch_stats(token, range_slug):
    request = urllib.request.Request(
        API_STATS_URL + range_slug,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = {
            401: "认证失败：token 无效、过期，或误用了 write-only 的插件 API key。",
            403: "该 token 缺少读取统计（read_stats）的权限。",
        }.get(error.code, f"上游返回 HTTP {error.code}。")
        raise SystemExit(f"fetch: WakaTime stats 请求失败：{detail}") from error


def snapshot_from_response(payload, range_slug, fetched_at):
    """Map the stats API response onto the minimal public snapshot fields."""
    data = payload["data"]
    if data.get("is_up_to_date") is False:
        raise SystemExit("fetch: 远端统计尚未聚合完成（is_up_to_date=false），请稍后重试。")
    total_seconds = float(
        data.get("total_seconds_including_other_language") or data.get("total_seconds") or 0
    )
    if total_seconds <= 0:
        raise SystemExit("fetch: 该区间没有可展示的编码时间，已保留现有快照。")
    daily_seconds = float(
        data.get("daily_average_including_other_language")
        or data.get("daily_average")
        or 0
    )
    if daily_seconds <= 0:
        daily_seconds = total_seconds / RANGE_DAYS[range_slug]

    def top(key, count, excluded=()):
        entries = []
        for item in data.get(key) or []:
            if item.get("name") in excluded or len(entries) == count:
                continue
            duration = float(item.get("total_seconds") or 0)
            entries.append({
                "name": str(item["name"]),
                "percent": float(item["percent"]),
                "text": str(item.get("text") or (format_duration(duration) if duration > 0 else "")),
            })
        return entries

    languages = top("languages", MAX_LANGUAGES, EXCLUDED_LANGUAGE_NAMES)
    if not languages:
        raise SystemExit("fetch: 过滤归并类别后没有可展示的语言，已保留现有快照。")
    snapshot = {
        "placeholder": False,
        "fetched_at": fetched_at,
        "range": range_slug,
        "total": {
            "seconds": round(total_seconds),
            "text": str(
                data.get("human_readable_total_including_other_language")
                or data.get("human_readable_total")
                or format_duration(total_seconds)
            ),
        },
        "daily_average": {
            "seconds": round(daily_seconds),
            "text": str(
                data.get("human_readable_daily_average") or format_duration(daily_seconds)
            ),
        },
        "languages": languages,
        "editors": top("editors", MAX_EDITORS),
        "operating_systems": top("operating_systems", MAX_OPERATING_SYSTEMS),
    }
    return validate_wakatime(snapshot)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="抓取 WakaTime 编码统计并写入 gen/hero/wakatime.json；默认 dry-run，仅校验并预览。",
        epilog="""默认只预览，不写文件；抓取失败时保留现有快照。
示例：
  python -I scripts/fetch_wakatime.py            抓取并预览将写入的统计
  python -I scripts/fetch_wakatime.py --apply    写入 gen/hero/wakatime.json""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--range", choices=sorted(RANGE_DAYS), default="last_7_days",
                        help="统计区间，默认 last_7_days")
    parser.add_argument("--apply", action="store_true",
                        help="写入 gen/hero/wakatime.json；默认只预览不写文件")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_PATH,
                        help=f"OAuth token 文件路径，默认 {DEFAULT_TOKEN_PATH.relative_to(ROOT)}")
    args = parser.parse_args()

    token = load_token(args.token_file)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot = snapshot_from_response(fetch_stats(token, args.range), args.range, fetched_at)
    top_language = snapshot["languages"][0]
    print(
        f"stats: {snapshot['range']} total {snapshot['total']['text']}"
        f" · daily {snapshot['daily_average']['text']}"
        f" · top {top_language['name']} {top_language['percent']}%  success"
    )
    if args.apply:
        write_json(WAKATIME_PATH, snapshot)
        print(f"write: {WAKATIME_PATH.relative_to(ROOT)}  success")
    else:
        print("dry-run: 未写入文件；加 --apply 写入 gen/hero/wakatime.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
