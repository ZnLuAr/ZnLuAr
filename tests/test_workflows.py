import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"


class WorkflowTests(unittest.TestCase):
    def test_wakatime_sync_keeps_credentials_out_and_scope_tight(self):
        content = (WORKFLOWS_DIR / "update-wakatime-stats.yml").read_text(encoding="utf-8")
        # 凭据只经 secret 环境变量进入；前缀说明字样允许，带密钥体的真实 token 不允许
        self.assertIsNone(re.search(r"waka_(?:tok|sec)_[A-Za-z0-9]{8,}", content))
        self.assertIn("WAKATIME_OAUTH_TOKEN: ${{ secrets.WAKATIME_OAUTH_TOKEN }}", content)
        # 权限只开 contents；定时与手动触发并存
        self.assertIn("contents: write", content)
        self.assertIn("schedule:", content)
        self.assertIn("workflow_dispatch:", content)
        # 与本地管线同构：抓取落盘后重建产物
        self.assertIn("scripts/fetch_wakatime.py --apply", content)
        self.assertIn("scripts/build_hero.py", content)
        # bot 身份提交，无变化时静默退出；提交范围不触碰 README 文案
        self.assertIn("github-actions[bot]", content)
        self.assertIn("git diff --quiet -- gen/hero/wakatime.json assets/hero", content)

    def test_ci_stays_zero_dependency(self):
        content = (WORKFLOWS_DIR / "ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("pip install", content.lower())
        self.assertIn("python -m unittest discover -s tests", content)
        self.assertIn("scripts/build_hero.py --check", content)


if __name__ == "__main__":
    unittest.main()
