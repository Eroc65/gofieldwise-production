"""Basic unit tests for the startup operations platform.

These tests do NOT require real API credentials — all external calls are
mocked so the suite can run offline in CI.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from autogpt.config import Config


def _make_config(**overrides) -> Config:
    """Return a Config with dummy credentials (safe for unit tests)."""
    cfg = Config()
    cfg.openai_api_key = overrides.get("openai_api_key", "test-key")
    cfg.github_token = overrides.get("github_token", "ghp_test")
    cfg.github_org = overrides.get("github_org", "")
    cfg.render_api_key = overrides.get("render_api_key", "rnd_test")
    cfg.render_owner_id = overrides.get("render_owner_id", "owner123")
    cfg.database_url = overrides.get("database_url", "postgresql://u:p@h/db")
    cfg.twitter_bearer_token = overrides.get("twitter_bearer_token", "bearer_test")
    cfg.twitter_api_key = overrides.get("twitter_api_key", "api_key")
    cfg.twitter_api_secret = overrides.get("twitter_api_secret", "api_secret")
    cfg.twitter_access_token = overrides.get("twitter_access_token", "access_token")
    cfg.twitter_access_secret = overrides.get("twitter_access_secret", "access_secret")
    cfg.meta_access_token = overrides.get("meta_access_token", "meta_token")
    cfg.meta_ad_account_id = overrides.get("meta_ad_account_id", "12345")
    cfg.verbose = False
    return cfg


# ======================================================================
# Config tests
# ======================================================================

class TestConfig(unittest.TestCase):
    def test_validate_raises_without_openai_key(self):
        cfg = _make_config(openai_api_key="")
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_passes_with_key(self):
        cfg = _make_config()
        cfg.validate()  # should not raise


# ======================================================================
# GitHubTools tests
# ======================================================================

class TestGitHubTools(unittest.TestCase):
    def setUp(self):
        from autogpt.tools.github_tools import GitHubTools
        self.tools = GitHubTools(token="ghp_test", verbose=False)

    @patch("autogpt.tools.github_tools.requests.post")
    def test_create_repo(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"id": 1, "name": "myrepo", "html_url": "https://github.com/u/myrepo"},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        result = self.tools.create_repo("myrepo")
        self.assertEqual(result["name"], "myrepo")
        mock_post.assert_called_once()

    @patch("autogpt.tools.github_tools.requests.put")
    @patch("autogpt.tools.github_tools.requests.get")
    def test_create_file_new(self, mock_get, mock_put):
        mock_get.return_value = MagicMock(status_code=404)
        mock_put.return_value = MagicMock(
            status_code=201,
            json=lambda: {"content": {"name": "README.md"}},
        )
        mock_put.return_value.raise_for_status = MagicMock()
        import base64
        result = self.tools.create_file(
            "owner", "repo", "README.md",
            base64.b64encode(b"hello").decode(),
            "Initial commit",
        )
        self.assertIn("content", result)
        mock_put.assert_called_once()


# ======================================================================
# EngineeringAgent tests
# ======================================================================

class TestEngineeringAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    @patch("autogpt.agents.engineering_agent.openai")
    @patch("autogpt.agents.engineering_agent.RenderTools")
    @patch("autogpt.agents.engineering_agent.GitHubTools")
    def test_run_returns_expected_keys(self, mock_gh_cls, mock_render_cls, mock_openai):
        # Mock GPT plan
        plan = {
            "repo_name": "flask-app",
            "description": "A simple Flask app",
            "files": {"main.py": "from flask import Flask\napp = Flask(__name__)"},
            "build_command": "pip install flask",
            "start_command": "python main.py",
            "env_vars": {},
        }
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(plan)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        # Mock GitHub
        mock_gh = MagicMock()
        mock_gh.create_repo.return_value = {
            "html_url": "https://github.com/u/flask-app",
            "clone_url": "https://github.com/u/flask-app.git",
            "owner": {"login": "u"},
        }
        mock_gh_cls.return_value = mock_gh

        # Mock Render
        mock_render = MagicMock()
        mock_render.create_postgres.return_value = {"id": "db-1", "name": "flask-app-db"}
        mock_render.create_web_service.return_value = {
            "id": "svc-1",
            "serviceDetails": {"url": "https://flask-app.onrender.com"},
        }
        mock_render_cls.return_value = mock_render

        from autogpt.agents.engineering_agent import EngineeringAgent
        agent = EngineeringAgent(self.cfg)
        result = agent.run("Build a Flask hello-world app")

        self.assertIn("repo_url", result)
        self.assertIn("deploy_url", result)
        self.assertIn("db_info", result)
        self.assertEqual(result["status"], "deployed")


# ======================================================================
# BrowserAgent tests
# ======================================================================

class TestBrowserAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    @patch("autogpt.agents.browser_agent.openai")
    def test_plan_returns_list(self, mock_openai):
        steps = [
            {"action": "navigate", "url": "https://example.com"},
            {"action": "screenshot", "path": "out.png"},
        ]
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(steps)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.browser_agent import BrowserAgent
        agent = BrowserAgent(self.cfg)
        result = agent._plan("Go to example.com and screenshot it")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["action"], "navigate")

    @patch("autogpt.agents.browser_agent.openai")
    def test_plan_handles_invalid_json(self, mock_openai):
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.browser_agent import BrowserAgent
        agent = BrowserAgent(self.cfg)
        result = agent._plan("do something")
        self.assertEqual(result, [])


# ======================================================================
# TwitterAgent tests
# ======================================================================

class TestTwitterAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    @patch("autogpt.agents.twitter_agent.openai")
    @patch("autogpt.agents.twitter_agent.TwitterAgent._build_client")
    def test_compose_and_post(self, mock_build, mock_openai):
        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": "123"})
        mock_build.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content="We launched! 🚀 #startup"))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.twitter_agent import TwitterAgent
        agent = TwitterAgent(self.cfg)
        result = agent.compose_and_post("We just launched our product!")
        self.assertEqual(result.get("id"), "123")
        mock_client.create_tweet.assert_called_once()


# ======================================================================
# MetaAdsAgent tests
# ======================================================================

class TestMetaAdsAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    @patch("autogpt.agents.meta_ads_agent.openai")
    def test_generate_ad_copy(self, mock_openai):
        copy = {"headline": "Best App Ever", "body": "Try it free.", "cta": "Sign Up"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(copy)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.meta_ads_agent import MetaAdsAgent
        agent = MetaAdsAgent(self.cfg)
        result = agent.generate_ad_copy("SaaS app for startups")
        self.assertEqual(result["headline"], "Best App Ever")
        self.assertEqual(result["cta"], "Sign Up")

    @patch("autogpt.agents.meta_ads_agent.openai")
    def test_generate_ad_copy_invalid_json_fallback(self, mock_openai):
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content="Buy now!"))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.meta_ads_agent import MetaAdsAgent
        agent = MetaAdsAgent(self.cfg)
        result = agent.generate_ad_copy("some product")
        self.assertIn("body", result)
        self.assertEqual(result["cta"], "Learn More")


# ======================================================================
# Orchestrator tests
# ======================================================================

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    @patch("autogpt.orchestrator.openai")
    def test_chat_direct_reply(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Hello there!"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(routing)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg)
        reply = orc.chat("Hi!")
        self.assertEqual(reply, "Hello there!")

    @patch("autogpt.orchestrator.openai")
    def test_chat_adds_to_history(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Sure!"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(routing)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg)
        orc.chat("Hello")
        # system + user + assistant = 3
        self.assertEqual(len(orc._history), 3)

    def test_reset_clears_history(self):
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg)
        orc._history.append({"role": "user", "content": "test"})
        orc.reset()
        self.assertEqual(len(orc._history), 1)
        self.assertEqual(orc._history[0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
