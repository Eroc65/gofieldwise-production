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
    cfg.telegram_bot_token = overrides.get("telegram_bot_token", "tg_test_token")
    cfg.telegram_default_chat_id = overrides.get("telegram_default_chat_id", "-100123456")
    cfg.youtube_api_key = overrides.get("youtube_api_key", "yt_api_key")
    cfg.youtube_channel_id = overrides.get("youtube_channel_id", "UCtest123")
    cfg.google_api_key = overrides.get("google_api_key", "google_test_key")
    cfg.google_search_engine_id = overrides.get("google_search_engine_id", "test_cx")
    cfg.yelp_api_key = overrides.get("yelp_api_key", "yelp_test_key")
    cfg.pinterest_access_token = overrides.get("pinterest_access_token", "pin_test_token")
    cfg.pinterest_default_board_id = overrides.get("pinterest_default_board_id", "board123")
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

    def test_session_id_auto_generated(self):
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg)
        self.assertIsNotNone(orc.session_id)
        self.assertTrue(len(orc.session_id) > 0)

    def test_session_id_explicit(self):
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="my-session-123")
        self.assertEqual(orc.session_id, "my-session-123")


# ======================================================================
# Orchestrator session persistence tests
# ======================================================================

class TestOrchestratorSessionPersistence(unittest.TestCase):
    """Verify Postgres session persistence using a mocked DatabaseTools."""

    def setUp(self):
        self.cfg = _make_config(database_url="postgresql://u:p@h/db")

    @patch("autogpt.orchestrator.Orchestrator._save_history")
    @patch("autogpt.orchestrator.Orchestrator._load_history")
    @patch("autogpt.orchestrator.Orchestrator._init_sessions_table")
    def test_db_methods_called_when_database_url_set(
        self, mock_init, mock_load, mock_save
    ):
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="sess-1")
        mock_init.assert_called_once()
        mock_load.assert_called_once()

    @patch("autogpt.orchestrator.Orchestrator._init_sessions_table")
    @patch("autogpt.tools.database_tools.DatabaseTools.query")
    @patch("autogpt.tools.database_tools.DatabaseTools._connect")
    def test_load_history_restores_turns(self, mock_connect, mock_query, mock_init):
        stored_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_query.return_value = [{"history": stored_history}]

        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="sess-restore")
        # system prompt + 2 restored turns
        self.assertEqual(len(orc._history), 3)
        self.assertEqual(orc._history[1]["role"], "user")
        self.assertEqual(orc._history[2]["role"], "assistant")

    @patch("autogpt.orchestrator.Orchestrator._init_sessions_table")
    @patch("autogpt.tools.database_tools.DatabaseTools.query")
    @patch("autogpt.tools.database_tools.DatabaseTools.execute_sql")
    @patch("autogpt.orchestrator.openai")
    def test_save_history_called_after_chat(
        self, mock_openai, mock_exec, mock_query, mock_init
    ):
        mock_query.return_value = []  # no existing session
        routing = {"agent": "none", "task": "", "direct_reply": "Done!"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(routing)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="sess-save")
        orc.chat("Hello")
        # execute_sql should have been called at least once for the upsert
        mock_exec.assert_called()

    @patch("autogpt.orchestrator.Orchestrator._init_sessions_table")
    @patch("autogpt.tools.database_tools.DatabaseTools.query")
    @patch("autogpt.tools.database_tools.DatabaseTools.execute_sql")
    def test_reset_saves_empty_history(self, mock_exec, mock_query, mock_init):
        mock_query.return_value = []
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="sess-reset")
        orc.reset()
        mock_exec.assert_called()

    @patch("autogpt.orchestrator.Orchestrator._init_sessions_table")
    @patch("autogpt.tools.database_tools.DatabaseTools.query")
    def test_load_history_skips_system_rows(self, mock_query, mock_init):
        """Stored system messages are not duplicated into history."""
        stored = [
            {"role": "system", "content": "old system prompt"},
            {"role": "user", "content": "A question"},
        ]
        mock_query.return_value = [{"history": stored}]
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg, session_id="sess-sys")
        # system (fresh) + user only; old system prompt dropped
        user_msgs = [m for m in orc._history if m["role"] == "user"]
        system_msgs = [m for m in orc._history if m["role"] == "system"]
        self.assertEqual(len(user_msgs), 1)
        self.assertEqual(len(system_msgs), 1)


# ======================================================================
# Web app tests
# ======================================================================

class TestWebApp(unittest.TestCase):
    """Test the FastAPI web application endpoints."""

    def setUp(self):
        self.cfg = _make_config()

    def _make_client(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")
        from autogpt.web.app import create_app
        return TestClient(create_app(self.cfg))

    def test_health_endpoint(self):
        client = self._make_client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_index_returns_html(self):
        client = self._make_client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Auto-GPT", resp.text)

    @patch("autogpt.orchestrator.openai")
    def test_post_chat_endpoint(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Hello from REST!"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(routing)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        client = self._make_client()
        resp = client.post(
            "/chat",
            json={"session_id": "test-session", "message": "Hi"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], "test-session")
        self.assertEqual(data["reply"], "Hello from REST!")

    @patch("autogpt.orchestrator.openai")
    def test_websocket_chat(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "WS reply!"}
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content=json.dumps(routing)))]
        mock_openai.chat.completions.create.return_value = mock_choice

        client = self._make_client()
        with client.websocket_connect("/ws/test-ws-session") as ws:
            ws.send_text("Hello over WebSocket")
            raw = ws.receive_text()
        data = json.loads(raw)
        self.assertEqual(data["reply"], "WS reply!")
        self.assertIn("agent", data)

    @patch("autogpt.orchestrator.openai")
    def test_websocket_session_reuse(self, mock_openai):
        """Two messages on the same WS session share one Orchestrator."""
        replies = [
            {"agent": "none", "task": "", "direct_reply": "First"},
            {"agent": "none", "task": "", "direct_reply": "Second"},
        ]
        mock_choice = MagicMock()
        mock_choice.choices = [
            MagicMock(message=MagicMock(content=json.dumps(r))) for r in replies
        ]
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(r)))]) for r in replies
        ]

        client = self._make_client()
        with client.websocket_connect("/ws/shared-session") as ws:
            ws.send_text("Message one")
            r1 = json.loads(ws.receive_text())["reply"]
            ws.send_text("Message two")
            r2 = json.loads(ws.receive_text())["reply"]

        self.assertEqual(r1, "First")
        self.assertEqual(r2, "Second")


# ======================================================================
# SlackAgent tests
# ======================================================================

class TestSlackAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.slack_webhook_url = "https://hooks.slack.com/test"
        self.cfg.slack_bot_token = "xoxb-test"
        self.cfg.slack_default_channel = "general"

    @patch("autogpt.agents.slack_agent.requests.post")
    def test_send_notification_success(self, mock_post):
        mock_post.return_value = MagicMock(ok=True, status_code=200, text="ok")
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.send_notification("Hello Slack!")
        self.assertTrue(result["ok"])
        mock_post.assert_called_once_with(
            "https://hooks.slack.com/test",
            json={"text": "Hello Slack!"},
            timeout=15,
        )

    @patch("autogpt.agents.slack_agent.requests.post")
    def test_send_notification_failure(self, mock_post):
        mock_post.return_value = MagicMock(ok=False, status_code=400, text="invalid_payload")
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.send_notification("Boom")
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    def test_send_notification_raises_without_webhook(self):
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        with self.assertRaises(RuntimeError):
            agent.send_notification("test")

    @patch("autogpt.agents.slack_agent.requests.post")
    def test_post_message_uses_api_when_bot_token_set(self, mock_post):
        mock_post.return_value = MagicMock(
            ok=True, status_code=200,
            json=lambda: {"ok": True, "ts": "12345.6789"},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.post_message("Hello channel!", channel="engineering")
        self.assertTrue(result["ok"])
        args, kwargs = mock_post.call_args
        self.assertIn("chat.postMessage", args[0])

    @patch("autogpt.agents.slack_agent.requests.post")
    def test_post_message_falls_back_to_webhook(self, mock_post):
        """With no bot token but a webhook URL, falls back to the webhook."""
        self.cfg.slack_bot_token = ""
        mock_post.return_value = MagicMock(ok=True, status_code=200, text="ok")
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.post_message("Fallback message")
        self.assertTrue(result["ok"])
        # Should have called the webhook URL
        mock_post.assert_called_once()
        self.assertIn("hooks.slack.com", mock_post.call_args[0][0])

    @patch("autogpt.agents.slack_agent.openai")
    @patch("autogpt.agents.slack_agent.requests.post")
    def test_compose_and_send(self, mock_post, mock_openai):
        mock_post.return_value = MagicMock(
            ok=True, status_code=200,
            json=lambda: {"ok": True},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        mock_choice = MagicMock()
        mock_choice.choices = [MagicMock(message=MagicMock(content="We just launched 🚀"))]
        mock_openai.chat.completions.create.return_value = mock_choice

        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.compose_and_send("announce our product launch")
        self.assertIn("ok", result)

    @patch("autogpt.agents.slack_agent.requests.post")
    def test_notify_task_result_noop_when_unconfigured(self, mock_post):
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""
        from autogpt.agents.slack_agent import SlackAgent
        agent = SlackAgent(self.cfg)
        result = agent.notify_task_result("engineering", "build an app", "Done!")
        self.assertFalse(result.get("ok"))
        mock_post.assert_not_called()


# ======================================================================
# Orchestrator Slack integration tests
# ======================================================================

class TestOrchestratorSlackIntegration(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""  # disable DB
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""

    @patch("autogpt.orchestrator.openai")
    def test_slack_agent_routed_correctly(self, mock_openai):
        routing = {"agent": "slack", "task": "announce our launch", "direct_reply": ""}
        slack_reply = {"agent": "none", "task": "", "direct_reply": "Message sent!"}
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]),
            # summarise call
            MagicMock(choices=[MagicMock(message=MagicMock(content="Slack message sent."))]),
        ]

        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.slack_agent import SlackAgent

        with patch.object(SlackAgent, "compose_and_send", return_value={"ok": True}) as mock_send:
            orc = Orchestrator(self.cfg)
            reply = orc.chat("Send a Slack message about our launch")
            mock_send.assert_called_once()


# ======================================================================
# TaskScheduler tests
# ======================================================================

class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""  # no real DB in tests
        self.cfg.scheduler_enabled = True

    def _make_scheduler(self):
        try:
            from autogpt.scheduler import TaskScheduler
        except ImportError:
            self.skipTest("apscheduler not installed")
        return TaskScheduler(self.cfg)

    def test_scheduler_starts_and_stops(self):
        sched = self._make_scheduler()
        sched.start()
        self.assertTrue(sched.running)
        sched.shutdown(wait=False)
        self.assertFalse(sched.running)

    def test_add_and_list_job_interval(self):
        sched = self._make_scheduler()
        sched.start()
        try:
            jid = sched.add_job(
                task="Check ad performance",
                trigger_type="interval",
                trigger_params={"hours": 24},
            )
            self.assertIsNotNone(jid)
            jobs = sched.list_jobs()
            job_ids = [j["job_id"] for j in jobs]
            self.assertIn(jid, job_ids)
        finally:
            sched.shutdown(wait=False)

    def test_remove_job(self):
        sched = self._make_scheduler()
        sched.start()
        try:
            jid = sched.add_job(
                task="Tweet daily update",
                trigger_type="cron",
                trigger_params={"hour": 8},
            )
            sched.remove_job(jid)
            jobs = sched.list_jobs()
            job_ids = [j["job_id"] for j in jobs]
            self.assertNotIn(jid, job_ids)
        finally:
            sched.shutdown(wait=False)

    def test_add_job_with_explicit_id(self):
        sched = self._make_scheduler()
        sched.start()
        try:
            jid = sched.add_job(
                task="Send weekly report",
                trigger_type="cron",
                trigger_params={"day_of_week": "mon", "hour": 9},
                job_id="weekly-report",
            )
            self.assertEqual(jid, "weekly-report")
        finally:
            sched.shutdown(wait=False)

    def test_unknown_trigger_raises(self):
        sched = self._make_scheduler()
        sched.start()
        try:
            with self.assertRaises(ValueError):
                sched.add_job(
                    task="Bad trigger",
                    trigger_type="unknown",
                    trigger_params={},
                )
        finally:
            sched.shutdown(wait=False)

    @patch("autogpt.scheduler.TaskScheduler._persist_job")
    @patch("autogpt.scheduler.TaskScheduler._delete_job")
    def test_db_methods_called_when_database_url_set(self, mock_delete, mock_persist):
        self.cfg.database_url = "postgresql://u:p@h/db"
        sched = self._make_scheduler()
        sched._init_jobs_table = MagicMock()
        sched._reload_jobs = MagicMock()
        sched.start()
        try:
            jid = sched.add_job(
                task="persist test",
                trigger_type="interval",
                trigger_params={"minutes": 30},
            )
            mock_persist.assert_called_once()
            sched.remove_job(jid)
            mock_delete.assert_called_once_with(jid)
        finally:
            sched.shutdown(wait=False)


# ======================================================================
# Web app — new endpoints tests
# ======================================================================

class TestWebAppNewEndpoints(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""
        self.cfg.scheduler_enabled = False  # disable scheduler in tests

    def _make_client(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")
        from autogpt.web.app import create_app
        return TestClient(create_app(self.cfg))

    def test_list_sessions_empty(self):
        client = self._make_client()
        resp = client.get("/sessions")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("sessions", resp.json())

    @patch("autogpt.orchestrator.openai")
    def test_list_sessions_after_chat(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Hi!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        client = self._make_client()
        client.post("/chat", json={"session_id": "sess-A", "message": "hello"})
        resp = client.get("/sessions")
        sessions = resp.json()["sessions"]
        self.assertTrue(any(s["session_id"] == "sess-A" for s in sessions))

    @patch("autogpt.orchestrator.openai")
    def test_get_history(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Done!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        client = self._make_client()
        client.post("/chat", json={"session_id": "hist-sess", "message": "Do something"})
        resp = client.get("/history/hist-sess")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session_id"], "hist-sess")
        # Should have user + assistant turns (no system)
        roles = [m["role"] for m in data["messages"]]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)
        self.assertNotIn("system", roles)

    @patch("autogpt.orchestrator.openai")
    def test_reset_session(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Ok!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        client = self._make_client()
        client.post("/chat", json={"session_id": "reset-sess", "message": "hello"})
        resp = client.delete("/sessions/reset-sess")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "reset")
        # History should be empty after reset
        hist_resp = client.get("/history/reset-sess")
        self.assertEqual(len(hist_resp.json()["messages"]), 0)

    def test_list_jobs_when_scheduler_disabled(self):
        """GET /jobs returns empty list when scheduler is off."""
        client = self._make_client()
        resp = client.get("/jobs")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"jobs": []})

    def test_create_job_when_scheduler_disabled_returns_503(self):
        client = self._make_client()
        resp = client.post(
            "/jobs",
            json={
                "task": "test task",
                "trigger_type": "interval",
                "trigger_params": {"hours": 1},
            },
        )
        self.assertEqual(resp.status_code, 503)

    def test_delete_job_when_scheduler_disabled_returns_503(self):
        client = self._make_client()
        resp = client.delete("/jobs/fake-job-id")
        self.assertEqual(resp.status_code, 503)




# ======================================================================
# EmailAgent tests
# ======================================================================

class TestEmailAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.email_sendgrid_api_key = "SG.test-key"
        self.cfg.email_from_address = "noreply@test.com"
        self.cfg.email_default_to = "founders@test.com"
        self.cfg.email_smtp_host = ""
        self.cfg.email_smtp_port = 587
        self.cfg.email_smtp_user = ""
        self.cfg.email_smtp_password = ""

    @patch("autogpt.agents.email_agent.requests.post")
    def test_send_email_via_sendgrid_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=202, text="")
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_email("to@test.com", "Subject", "Body")
        self.assertTrue(result["ok"])
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("sendgrid.com", args[0])

    @patch("autogpt.agents.email_agent.requests.post")
    def test_send_email_via_sendgrid_failure(self, mock_post):
        mock_post.return_value = MagicMock(status_code=403, text="Unauthorized")
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_email("to@test.com", "Subject", "Body")
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    @patch("autogpt.agents.email_agent.requests.post")
    def test_send_email_to_multiple_recipients(self, mock_post):
        mock_post.return_value = MagicMock(status_code=202, text="")
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_email(["a@test.com", "b@test.com"], "Hi", "Hello")
        self.assertTrue(result["ok"])
        payload = mock_post.call_args[1]["json"]
        tos = payload["personalizations"][0]["to"]
        self.assertEqual(len(tos), 2)

    def test_send_email_raises_without_credentials(self):
        self.cfg.email_sendgrid_api_key = ""
        self.cfg.email_smtp_host = ""
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        with self.assertRaises(RuntimeError):
            agent.send_email("to@test.com", "Subject", "Body")

    @patch("autogpt.agents.email_agent.smtplib.SMTP")
    def test_send_email_via_smtp(self, mock_smtp_cls):
        self.cfg.email_sendgrid_api_key = ""
        self.cfg.email_smtp_host = "smtp.example.com"
        self.cfg.email_smtp_user = "user@example.com"
        self.cfg.email_smtp_password = "pass"

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_email("to@test.com", "Subject", "Body")
        self.assertTrue(result["ok"])
        mock_server.sendmail.assert_called_once()

    @patch("autogpt.agents.email_agent.smtplib.SMTP")
    def test_send_email_smtp_error_returns_not_ok(self, mock_smtp_cls):
        self.cfg.email_sendgrid_api_key = ""
        self.cfg.email_smtp_host = "smtp.example.com"
        mock_smtp_cls.side_effect = OSError("Connection refused")
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_email("to@test.com", "Subject", "Body")
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    @patch("autogpt.agents.email_agent.requests.post")
    @patch("autogpt.agents.email_agent.openai")
    def test_compose_and_send(self, mock_openai, mock_post):
        mock_post.return_value = MagicMock(status_code=202, text="")
        composed = {"subject": "Launch!", "body": "We just launched our product."}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(composed)))]
        )
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.compose_and_send("announce our product launch")
        self.assertTrue(result["ok"])

    @patch("autogpt.agents.email_agent.requests.post")
    def test_send_report(self, mock_post):
        mock_post.return_value = MagicMock(status_code=202, text="")
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.send_report("Weekly Report", "This week we grew 10%.")
        self.assertTrue(result["ok"])

    def test_compose_and_send_raises_without_recipient(self):
        self.cfg.email_default_to = ""
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        with self.assertRaises(RuntimeError):
            agent.compose_and_send("some brief")

    @patch("autogpt.agents.email_agent.requests.post")
    @patch("autogpt.agents.email_agent.openai")
    def test_compose_and_send_invalid_json_fallback(self, mock_openai, mock_post):
        """When GPT returns non-JSON, compose_and_send uses raw text as body."""
        mock_post.return_value = MagicMock(status_code=202, text="")
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Just send this."))]
        )
        from autogpt.agents.email_agent import EmailAgent
        agent = EmailAgent(self.cfg)
        result = agent.compose_and_send("some brief")
        self.assertTrue(result["ok"])


# ======================================================================
# AnalyticsAgent tests
# ======================================================================

class TestAnalyticsAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        # Disable external service credentials so collect_metrics returns quickly
        self.cfg.twitter_bearer_token = ""
        self.cfg.meta_access_token = ""
        self.cfg.meta_ad_account_id = ""
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""
        self.cfg.email_sendgrid_api_key = ""
        self.cfg.email_smtp_host = ""
        self.cfg.email_default_to = ""

    @patch("autogpt.agents.analytics_agent.openai")
    def test_generate_report_returns_string(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="This week was great."))]
        )
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        report = agent.generate_report(metrics={"period_days": 7})
        self.assertIsInstance(report, str)
        self.assertEqual(report, "This week was great.")

    @patch("autogpt.agents.analytics_agent.openai")
    def test_generate_report_calls_collect_when_no_metrics(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Report text."))]
        )
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        report = agent.generate_report()
        self.assertIsInstance(report, str)

    def test_collect_metrics_returns_dict_without_credentials(self):
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        metrics = agent.collect_metrics()
        self.assertIn("period_days", metrics)
        self.assertNotIn("twitter", metrics)
        self.assertNotIn("meta_ads", metrics)

    def test_deliver_report_skips_channels_when_unconfigured(self):
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        result = agent.deliver_report("Weekly report text.")
        self.assertEqual(result["email"]["skipped"], True)
        self.assertEqual(result["slack"]["skipped"], True)

    @patch("autogpt.agents.analytics_agent.openai")
    def test_run_returns_expected_keys(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Good week."))]
        )
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        result = agent.run("Generate a weekly report")
        self.assertIn("report", result)
        self.assertIn("delivery", result)
        self.assertIn("metrics", result)
        self.assertIsInstance(result["report"], str)

    @patch("autogpt.agents.analytics_agent.requests.get")
    @patch("autogpt.agents.analytics_agent.openai")
    def test_collect_meta_metrics(self, mock_openai, mock_get):
        self.cfg.meta_access_token = "meta_token"
        self.cfg.meta_ad_account_id = "12345"
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {
                "data": [{"spend": "100", "impressions": "5000", "clicks": "200", "ctr": "4.0"}]
            },
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Good."))]
        )
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        metrics = agent.collect_metrics()
        self.assertIn("meta_ads", metrics)
        self.assertEqual(metrics["meta_ads"]["spend"], "100")

    @patch("autogpt.agents.analytics_agent.openai")
    @patch("autogpt.agents.email_agent.requests.post")
    def test_deliver_report_via_email(self, mock_post, mock_openai):
        self.cfg.email_sendgrid_api_key = "SG.test"
        self.cfg.email_from_address = "noreply@test.com"
        self.cfg.email_default_to = "founders@test.com"
        mock_post.return_value = MagicMock(status_code=202, text="")
        from autogpt.agents.analytics_agent import AnalyticsAgent
        agent = AnalyticsAgent(self.cfg)
        result = agent.deliver_report("Report body")
        self.assertTrue(result["email"]["ok"])


# ======================================================================
# Orchestrator — email and analytics routing tests
# ======================================================================

class TestOrchestratorNewAgents(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""

    @patch("autogpt.orchestrator.openai")
    def test_email_agent_routed(self, mock_openai):
        routing = {"agent": "email", "task": "announce our launch", "direct_reply": ""}
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Email sent."))]),
        ]
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.email_agent import EmailAgent

        with patch.object(EmailAgent, "compose_and_send", return_value={"ok": True}):
            orc = Orchestrator(self.cfg)
            orc.chat("Send an email about our launch")
            self.assertEqual(orc.last_agent, "email")

    @patch("autogpt.orchestrator.openai")
    def test_analytics_agent_routed(self, mock_openai):
        routing = {"agent": "analytics", "task": "generate weekly report", "direct_reply": ""}
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Report generated."))]),
        ]
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.analytics_agent import AnalyticsAgent

        with patch.object(
            AnalyticsAgent, "run",
            return_value={"report": "Good week.", "delivery": {}, "metrics": {}}
        ):
            orc = Orchestrator(self.cfg)
            orc.chat("Generate the weekly report")
            self.assertEqual(orc.last_agent, "analytics")

    @patch("autogpt.orchestrator.openai")
    def test_last_agent_is_none_for_direct_reply(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Hello!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        from autogpt.orchestrator import Orchestrator
        orc = Orchestrator(self.cfg)
        orc.chat("Hi")
        self.assertEqual(orc.last_agent, "none")


# ======================================================================
# Web app — API key middleware tests
# ======================================================================

class TestWebAppApiKeyMiddleware(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""
        self.cfg.scheduler_enabled = False
        self.cfg.web_api_key = "secret-key-123"

    def _make_client(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")
        from autogpt.web.app import create_app
        return TestClient(create_app(self.cfg))

    def test_health_accessible_without_api_key(self):
        client = self._make_client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_index_accessible_without_api_key(self):
        client = self._make_client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_sessions_blocked_without_api_key(self):
        client = self._make_client()
        resp = client.get("/sessions")
        self.assertEqual(resp.status_code, 401)

    def test_sessions_accessible_with_correct_api_key(self):
        client = self._make_client()
        resp = client.get("/sessions", headers={"X-API-Key": "secret-key-123"})
        self.assertEqual(resp.status_code, 200)

    def test_sessions_blocked_with_wrong_api_key(self):
        client = self._make_client()
        resp = client.get("/sessions", headers={"X-API-Key": "wrong-key"})
        self.assertEqual(resp.status_code, 401)

    @patch("autogpt.orchestrator.openai")
    def test_chat_endpoint_blocked_without_api_key(self, mock_openai):
        client = self._make_client()
        resp = client.post("/chat", json={"session_id": "s1", "message": "hi"})
        self.assertEqual(resp.status_code, 401)

    @patch("autogpt.orchestrator.openai")
    def test_chat_endpoint_accessible_with_api_key(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Hi!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        client = self._make_client()
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "hi"},
            headers={"X-API-Key": "secret-key-123"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_no_auth_when_api_key_not_configured(self):
        self.cfg.web_api_key = ""
        client = self._make_client()
        resp = client.get("/sessions")
        self.assertEqual(resp.status_code, 200)


# ======================================================================
# Web app — WebSocket JSON response tests
# ======================================================================

class TestWebAppWebSocketJson(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""
        self.cfg.scheduler_enabled = False
        self.cfg.web_api_key = ""

    def _make_client(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")
        from autogpt.web.app import create_app
        return TestClient(create_app(self.cfg))

    @patch("autogpt.orchestrator.openai")
    def test_websocket_reply_includes_agent_field(self, mock_openai):
        routing = {"agent": "none", "task": "", "direct_reply": "Howdy!"}
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]
        )
        client = self._make_client()
        with client.websocket_connect("/ws/json-test-session") as ws:
            ws.send_text("Hello")
            raw = ws.receive_text()
        data = json.loads(raw)
        self.assertIn("reply", data)
        self.assertIn("agent", data)
        self.assertEqual(data["reply"], "Howdy!")
        self.assertEqual(data["agent"], "none")




# ======================================================================
# CustomerSupportAgent tests
# ======================================================================

class TestCustomerSupportAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""  # in-memory mode for all tests
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""
        self.cfg.email_sendgrid_api_key = ""
        self.cfg.email_smtp_host = ""
        self.cfg.email_default_to = ""

    def _make_agent(self):
        from autogpt.agents.customer_support_agent import CustomerSupportAgent
        return CustomerSupportAgent(self.cfg)

    def test_add_article_in_memory(self):
        agent = self._make_agent()
        result = agent.add_article("How to reset password", "Go to settings and click reset.")
        self.assertIn("id", result)
        self.assertEqual(result["title"], "How to reset password")
        self.assertIn("created", result["status"])

    def test_list_articles_empty(self):
        agent = self._make_agent()
        articles = agent.list_articles()
        self.assertEqual(articles, [])

    def test_list_articles_after_add(self):
        agent = self._make_agent()
        agent.add_article("Billing FAQ", "We accept Visa and Mastercard.")
        agent.add_article("Refund Policy", "We offer 30-day refunds.")
        articles = agent.list_articles()
        self.assertEqual(len(articles), 2)

    def test_search_kb_finds_matching_article(self):
        agent = self._make_agent()
        agent.add_article("Password Reset", "Click Forgot Password on the login page.")
        agent.add_article("Billing", "We charge monthly on the 1st.")
        results = agent.search_kb("password")
        self.assertTrue(any("Password" in r["title"] for r in results))

    def test_search_kb_returns_empty_for_no_match(self):
        agent = self._make_agent()
        agent.add_article("Billing", "Monthly billing cycle.")
        results = agent.search_kb("refund policy for enterprise customers")
        self.assertIsInstance(results, list)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_answer_returns_expected_keys(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="You can reset your password in settings."))]
        )
        agent = self._make_agent()
        agent.add_article("Password Reset", "Click Forgot Password.")
        result = agent.answer("How do I reset my password?")
        self.assertIn("answer", result)
        self.assertIn("ticket_id", result)
        self.assertIn("kb_articles_used", result)
        self.assertIn("escalation_needed", result)
        self.assertIsInstance(result["ticket_id"], int)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_answer_logs_ticket_in_memory(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Here is the answer."))]
        )
        agent = self._make_agent()
        result = agent.answer("What is your refund policy?")
        self.assertGreater(result["ticket_id"], 0)
        self.assertEqual(len(agent._mem_tickets), 1)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_escalation_needed_detection(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content="I don't have enough information to answer this. Please contact support."
            ))]
        )
        agent = self._make_agent()
        result = agent.answer("What is the meaning of life?")
        self.assertTrue(result["escalation_needed"])

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_escalation_not_needed_for_clear_answer(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="You can reset your password in Account Settings."))]
        )
        agent = self._make_agent()
        agent.add_article("Password", "Account Settings → Security → Reset Password.")
        result = agent.answer("How do I reset my password?")
        self.assertFalse(result["escalation_needed"])

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_escalate_returns_skipped_when_unconfigured(self, mock_openai):
        agent = self._make_agent()
        # Manually create a ticket
        agent._mem_tickets.append({
            "id": 1, "question": "Can I get a refund?",
            "answer": "Unclear.", "status": "open"
        })
        result = agent.escalate(1)
        self.assertEqual(result["slack"]["skipped"], True)
        self.assertEqual(result["email"]["skipped"], True)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_escalate_unknown_ticket(self, mock_openai):
        agent = self._make_agent()
        result = agent.escalate(999)
        self.assertIn("error", result)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_run_routes_to_answer(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Here is the answer."))]
        )
        agent = self._make_agent()
        result = agent.run("How do I upgrade my plan?")
        self.assertIn("answer", result)

    def test_run_routes_to_add_article(self):
        agent = self._make_agent()
        result = agent.run("Add article: Pricing\nWe offer monthly and annual plans.")
        self.assertIn("id", result)

    def test_run_routes_to_list_articles(self):
        agent = self._make_agent()
        agent.add_article("FAQ", "Frequently asked questions.")
        result = agent.run("List articles in the knowledge base")
        self.assertIn("articles", result)
        self.assertIn("count", result)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_build_context_no_articles(self, mock_openai):
        from autogpt.agents.customer_support_agent import CustomerSupportAgent
        ctx = CustomerSupportAgent._build_context([])
        self.assertIn("No relevant", ctx)

    @patch("autogpt.agents.customer_support_agent.openai")
    def test_build_context_formats_articles(self, mock_openai):
        from autogpt.agents.customer_support_agent import CustomerSupportAgent
        articles = [
            {"title": "Returns", "content": "30-day return policy."},
            {"title": "Shipping", "content": "Free over $50."},
        ]
        ctx = CustomerSupportAgent._build_context(articles)
        self.assertIn("Returns", ctx)
        self.assertIn("Shipping", ctx)


# ======================================================================
# ContentAgent tests
# ======================================================================

class TestContentAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.content_agent import ContentAgent
        return ContentAgent(self.cfg)

    def _mock_gpt(self, mock_openai, content: dict):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(content)))]
        )

    @patch("autogpt.agents.content_agent.openai")
    def test_write_blog_post_returns_expected_keys(self, mock_openai):
        blog = {
            "title": "10 Tips for Startup Growth",
            "meta_description": "Discover proven growth tips.",
            "introduction": "Growth is hard.",
            "sections": [{"heading": "Tip 1", "body": "Start small."}],
            "conclusion": "Take action today.",
        }
        self._mock_gpt(mock_openai, blog)
        agent = self._make_agent()
        result = agent.write_blog_post("Tips for early-stage startup growth")
        self.assertIn("title", result)
        self.assertIn("sections", result)
        self.assertIn("conclusion", result)
        self.assertEqual(result["title"], "10 Tips for Startup Growth")

    @patch("autogpt.agents.content_agent.openai")
    def test_write_blog_post_invalid_json_fallback(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Here is a blog post about growth."))]
        )
        agent = self._make_agent()
        result = agent.write_blog_post("Growth strategies")
        self.assertIn("body", result)  # fallback key

    @patch("autogpt.agents.content_agent.openai")
    def test_write_landing_page_returns_expected_keys(self, mock_openai):
        lp = {
            "headline": "Launch Faster with AI",
            "subheadline": "Automate your startup operations.",
            "value_proposition": "Save 10 hours a week.",
            "features": [{"title": "Automation", "description": "Set it and forget it."}],
            "social_proof": "Loved by 500+ founders.",
            "cta_primary": "Get Started Free",
            "cta_secondary": "Watch Demo",
        }
        self._mock_gpt(mock_openai, lp)
        agent = self._make_agent()
        result = agent.write_landing_page("AI-powered startup operations platform")
        self.assertEqual(result["headline"], "Launch Faster with AI")
        self.assertIn("features", result)
        self.assertIn("cta_primary", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_write_social_content_twitter(self, mock_openai):
        post = {
            "post": "We just launched 🚀 Try it free today!",
            "hashtags": ["#startup", "#AI"],
            "notes": "Post on weekday morning.",
        }
        self._mock_gpt(mock_openai, post)
        agent = self._make_agent()
        result = agent.write_social_content("We launched our product!", platform="twitter")
        self.assertEqual(result["platform"], "twitter")
        self.assertIn("post", result)
        self.assertIn("hashtags", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_write_social_content_linkedin(self, mock_openai):
        post = {"post": "Excited to share...", "hashtags": ["#product"], "notes": ""}
        self._mock_gpt(mock_openai, post)
        agent = self._make_agent()
        result = agent.write_social_content("Product launch announcement", platform="linkedin")
        self.assertEqual(result["platform"], "linkedin")

    @patch("autogpt.agents.content_agent.openai")
    def test_write_social_content_unknown_platform_defaults_to_twitter(self, mock_openai):
        post = {"post": "Hello!", "hashtags": [], "notes": ""}
        self._mock_gpt(mock_openai, post)
        agent = self._make_agent()
        result = agent.write_social_content("Hello world", platform="tiktok")
        self.assertEqual(result["platform"], "twitter")

    @patch("autogpt.agents.content_agent.openai")
    def test_write_email_campaign_returns_expected_keys(self, mock_openai):
        campaign = {
            "subject": "You're invited to try our new feature",
            "preview_text": "Save time with automation.",
            "body": "Hi there, we just launched a new feature...",
        }
        self._mock_gpt(mock_openai, campaign)
        agent = self._make_agent()
        result = agent.write_email_campaign("Launch announcement for existing users")
        self.assertIn("subject", result)
        self.assertIn("preview_text", result)
        self.assertIn("body", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_run_routes_to_blog_post_by_default(self, mock_openai):
        blog = {"title": "Blog", "sections": [], "conclusion": "Done."}
        self._mock_gpt(mock_openai, blog)
        agent = self._make_agent()
        result = agent.run("Write an article about productivity for founders")
        self.assertIn("title", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_run_routes_to_landing_page(self, mock_openai):
        lp = {"headline": "Build Fast", "features": [], "cta_primary": "Try Now"}
        self._mock_gpt(mock_openai, lp)
        agent = self._make_agent()
        result = agent.run("Write landing page copy for our SaaS product")
        self.assertIn("headline", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_run_routes_to_linkedin(self, mock_openai):
        post = {"post": "Excited!", "hashtags": [], "notes": ""}
        self._mock_gpt(mock_openai, post)
        agent = self._make_agent()
        result = agent.run("Write a LinkedIn post about our funding round")
        self.assertEqual(result["platform"], "linkedin")

    @patch("autogpt.agents.content_agent.openai")
    def test_run_routes_to_email_campaign(self, mock_openai):
        campaign = {"subject": "Big news", "preview_text": "Read on.", "body": "We did it!"}
        self._mock_gpt(mock_openai, campaign)
        agent = self._make_agent()
        result = agent.run("Draft a newsletter for our latest product update")
        self.assertIn("subject", result)

    @patch("autogpt.agents.content_agent.openai")
    def test_run_routes_to_instagram(self, mock_openai):
        post = {"post": "Check it out!", "hashtags": ["#ai"], "notes": ""}
        self._mock_gpt(mock_openai, post)
        agent = self._make_agent()
        result = agent.run("Write an Instagram caption for our product launch")
        self.assertEqual(result["platform"], "instagram")


# ======================================================================
# Orchestrator — customer_support and content routing tests
# ======================================================================

class TestOrchestratorContentAndSupport(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""
        self.cfg.slack_webhook_url = ""
        self.cfg.slack_bot_token = ""

    @patch("autogpt.orchestrator.openai")
    def test_customer_support_routed(self, mock_openai):
        routing = {
            "agent": "customer_support",
            "task": "How do I reset my password?",
            "direct_reply": "",
        }
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Ticket logged."))]),
        ]
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.customer_support_agent import CustomerSupportAgent

        with patch.object(
            CustomerSupportAgent, "run",
            return_value={"answer": "Check settings.", "ticket_id": 1,
                          "kb_articles_used": 0, "escalation_needed": False}
        ):
            orc = Orchestrator(self.cfg)
            orc.chat("How do I reset my password?")
            self.assertEqual(orc.last_agent, "customer_support")

    @patch("autogpt.orchestrator.openai")
    def test_content_agent_routed(self, mock_openai):
        routing = {
            "agent": "content",
            "task": "Write a blog post about productivity",
            "direct_reply": "",
        }
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(routing)))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Blog post created."))]),
        ]
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.content_agent import ContentAgent

        with patch.object(
            ContentAgent, "run",
            return_value={"title": "Productivity Tips", "sections": [], "conclusion": "Go!"}
        ):
            orc = Orchestrator(self.cfg)
            orc.chat("Write a blog post about productivity")
            self.assertEqual(orc.last_agent, "content")


if __name__ == "__main__":
    unittest.main()


# ======================================================================
# TelegramAgent tests
# ======================================================================

class TestTelegramAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.telegram_agent import TelegramAgent
        return TelegramAgent(self.cfg)

    @patch("autogpt.agents.telegram_agent.requests")
    def test_send_message_calls_api(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 42}},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.send_message("Hello, Telegram!")
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args
        self.assertIn("sendMessage", call_kwargs[0][0])
        self.assertEqual(result["ok"], True)

    @patch("autogpt.agents.telegram_agent.requests")
    def test_send_message_uses_default_chat_id(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 7}},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.send_message("Broadcast!")
        payload = mock_requests.post.call_args[1]["json"]
        self.assertEqual(payload["chat_id"], self.cfg.telegram_default_chat_id)

    def test_send_message_raises_without_chat_id(self):
        self.cfg.telegram_default_chat_id = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.send_message("Hello!")

    def test_send_message_raises_without_token(self):
        self.cfg.telegram_bot_token = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.send_message("Hello!")

    @patch("autogpt.agents.telegram_agent.requests")
    @patch("autogpt.agents.telegram_agent.openai")
    def test_compose_and_send(self, mock_openai, mock_requests):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="🚀 We just launched!"))]
        )
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 10}},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.compose_and_send("Announce our product launch")
        self.assertIn("message", result)
        self.assertEqual(result["message"], "🚀 We just launched!")
        self.assertIn("api_response", result)

    @patch("autogpt.agents.telegram_agent.requests")
    def test_get_updates(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": [{"update_id": 1, "message": {"text": "hi"}}]},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        updates = agent.get_updates()
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["update_id"], 1)

    @patch("autogpt.agents.telegram_agent.requests")
    def test_get_updates_clamps_limit(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.get_updates(limit=200)
        payload = mock_requests.post.call_args[1]["json"]
        self.assertLessEqual(payload["limit"], 100)

    @patch("autogpt.agents.telegram_agent.requests")
    @patch("autogpt.agents.telegram_agent.openai")
    def test_run_routes_to_get_updates(self, mock_openai, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("get updates from Telegram bot")
        self.assertIn("updates", result)

    @patch("autogpt.agents.telegram_agent.requests")
    @patch("autogpt.agents.telegram_agent.openai")
    def test_run_routes_to_compose_and_send(self, mock_openai, mock_requests):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="New feature shipped!"))]
        )
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 5}},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("Announce our new pricing page")
        self.assertIn("message", result)


# ======================================================================
# YouTubeAgent tests
# ======================================================================

class TestYouTubeAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.youtube_agent import YouTubeAgent
        return YouTubeAgent(self.cfg)

    @patch("autogpt.agents.youtube_agent.requests")
    def test_search_videos_returns_list(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [
                    {"id": {"videoId": "abc123"}, "snippet": {
                        "title": "Test Video", "channelTitle": "TestChan",
                        "publishedAt": "2025-01-01", "description": "Desc"
                    }}
                ]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        results = agent.search_videos("startup growth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "abc123")
        self.assertEqual(results[0]["title"], "Test Video")

    @patch("autogpt.agents.youtube_agent.requests")
    def test_search_videos_clamps_max_results(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.search_videos("test", max_results=200)
        params = mock_requests.get.call_args[1]["params"]
        self.assertLessEqual(params["maxResults"], 50)

    def test_search_videos_raises_without_api_key(self):
        self.cfg.youtube_api_key = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.search_videos("test")

    @patch("autogpt.agents.youtube_agent.requests")
    def test_get_video_stats(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [{
                    "snippet": {"title": "My Video", "channelTitle": "Chan", "publishedAt": ""},
                    "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"}
                }]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        stats = agent.get_video_stats("abc123")
        self.assertEqual(stats["view_count"], 1000)
        self.assertEqual(stats["like_count"], 50)

    @patch("autogpt.agents.youtube_agent.requests")
    def test_get_video_stats_not_found(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.get_video_stats("unknown")
        self.assertIn("error", result)

    @patch("autogpt.agents.youtube_agent.requests")
    def test_get_channel_stats(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [{
                    "snippet": {"title": "My Channel", "description": "A channel"},
                    "statistics": {"subscriberCount": "5000", "videoCount": "200", "viewCount": "100000"}
                }]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        stats = agent.get_channel_stats()
        self.assertEqual(stats["subscriber_count"], 5000)
        self.assertEqual(stats["video_count"], 200)

    def test_get_channel_stats_raises_without_channel_id(self):
        self.cfg.youtube_channel_id = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.get_channel_stats()

    @patch("autogpt.agents.youtube_agent.openai")
    def test_summarise_calls_gpt(self, mock_openai):
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Great channel metrics."))]
        )
        agent = self._make_agent()
        summary = agent.summarise({"subscriber_count": 5000})
        self.assertEqual(summary, "Great channel metrics.")

    @patch("autogpt.agents.youtube_agent.openai")
    @patch("autogpt.agents.youtube_agent.requests")
    def test_run_channel_stats(self, mock_requests, mock_openai):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [{
                    "snippet": {"title": "Chan", "description": ""},
                    "statistics": {"subscriberCount": "1000", "videoCount": "50", "viewCount": "9999"}
                }]
            },
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Channel is growing."))]
        )
        agent = self._make_agent()
        result = agent.run("show my channel stats")
        self.assertIn("stats", result)
        self.assertIn("summary", result)

    @patch("autogpt.agents.youtube_agent.openai")
    @patch("autogpt.agents.youtube_agent.requests")
    def test_run_search_default(self, mock_requests, mock_openai):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": [{"id": {"videoId": "v1"}, "snippet": {
                "title": "T", "channelTitle": "C", "publishedAt": "", "description": ""
            }}]},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Found 1 video."))]
        )
        agent = self._make_agent()
        result = agent.run("search for Python tutorials")
        self.assertIn("videos", result)
        self.assertIn("summary", result)


# ======================================================================
# GoogleAgent tests
# ======================================================================

class TestGoogleAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.google_agent import GoogleAgent
        return GoogleAgent(self.cfg)

    @patch("autogpt.agents.google_agent.requests")
    @patch("autogpt.agents.google_agent.openai")
    def test_search_returns_results(self, mock_openai, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [
                    {"title": "Result 1", "link": "https://example.com/1", "snippet": "Snippet 1"},
                    {"title": "Result 2", "link": "https://example.com/2", "snippet": "Snippet 2"},
                ]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        results = agent.search("startup marketing")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Result 1")
        self.assertEqual(results[0]["link"], "https://example.com/1")

    @patch("autogpt.agents.google_agent.requests")
    def test_search_clamps_num_results(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.search("test", num_results=50)
        params = mock_requests.get.call_args[1]["params"]
        self.assertLessEqual(params["num"], 10)

    def test_search_raises_without_api_key(self):
        self.cfg.google_api_key = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.search("test")

    def test_search_raises_without_engine_id(self):
        self.cfg.google_search_engine_id = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.search("test")

    @patch("autogpt.agents.google_agent.requests")
    @patch("autogpt.agents.google_agent.openai")
    def test_search_and_summarise_returns_summary(self, mock_openai, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": [{"title": "T", "link": "https://x.com", "snippet": "S"}]},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Key findings: ..."))]
        )
        agent = self._make_agent()
        result = agent.search_and_summarise("AI trends 2025")
        self.assertIn("results", result)
        self.assertIn("summary", result)
        self.assertEqual(result["summary"], "Key findings: ...")

    @patch("autogpt.agents.google_agent.requests")
    @patch("autogpt.agents.google_agent.openai")
    def test_answer_question_returns_answer_and_sources(self, mock_openai, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": [{"title": "T", "link": "https://x.com", "snippet": "S"}]},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="The answer is 42."))]
        )
        agent = self._make_agent()
        result = agent.answer_question("What is the speed of light?")
        self.assertIn("answer", result)
        self.assertIn("sources", result)
        self.assertEqual(result["answer"], "The answer is 42.")

    @patch("autogpt.agents.google_agent.requests")
    @patch("autogpt.agents.google_agent.openai")
    def test_run_routes_to_answer_question(self, mock_openai, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Because gravity."))]
        )
        agent = self._make_agent()
        result = agent.run("What is product-market fit?")
        self.assertIn("answer", result)

    @patch("autogpt.agents.google_agent.requests")
    @patch("autogpt.agents.google_agent.openai")
    def test_run_routes_to_search_and_summarise(self, mock_openai, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": [{"title": "T", "link": "https://x.com", "snippet": "S"}]},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Trends summary."))]
        )
        agent = self._make_agent()
        result = agent.run("latest SaaS pricing trends")
        self.assertIn("results", result)
        self.assertIn("summary", result)

    @patch("autogpt.agents.google_agent.requests")
    def test_search_passes_date_restrict(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.search("news", date_restrict="d7")
        params = mock_requests.get.call_args[1]["params"]
        self.assertEqual(params["dateRestrict"], "d7")

    @patch("autogpt.agents.google_agent.requests")
    def test_search_passes_site_filter(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.search("blog posts", site_filter="techcrunch.com")
        params = mock_requests.get.call_args[1]["params"]
        self.assertIn("techcrunch.com", params["q"])


# ======================================================================
# YelpAgent tests
# ======================================================================

class TestYelpAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.yelp_agent import YelpAgent
        return YelpAgent(self.cfg)

    @patch("autogpt.agents.yelp_agent.requests")
    def test_search_businesses_returns_list(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "businesses": [
                    {
                        "id": "biz1", "name": "Coffee House", "rating": 4.5,
                        "review_count": 200, "location": {"display_address": ["123 Main St"]},
                        "display_phone": "555-1234", "categories": [{"title": "Coffee"}],
                        "url": "https://yelp.com/biz/1", "is_closed": False,
                    }
                ]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        results = agent.search_businesses("coffee", "San Francisco, CA")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Coffee House")
        self.assertEqual(results[0]["rating"], 4.5)

    def test_search_businesses_raises_without_api_key(self):
        self.cfg.yelp_api_key = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.search_businesses("coffee", "NYC")

    @patch("autogpt.agents.yelp_agent.requests")
    def test_get_business_returns_detail(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "id": "biz1", "name": "Pizza Place", "rating": 4.0,
                "review_count": 80, "display_phone": "555-9999",
                "location": {"display_address": ["456 Oak Ave"]},
                "hours": [], "categories": [{"title": "Pizza"}],
                "url": "https://yelp.com/biz/p", "photos": [],
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        detail = agent.get_business("biz1")
        self.assertEqual(detail["name"], "Pizza Place")
        self.assertEqual(detail["rating"], 4.0)

    @patch("autogpt.agents.yelp_agent.requests")
    def test_get_reviews_returns_list(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "reviews": [
                    {
                        "user": {"name": "Alice"},
                        "rating": 5,
                        "text": "Amazing!",
                        "time_created": "2025-01-01",
                        "url": "https://yelp.com/review/1",
                    }
                ]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        reviews = agent.get_reviews("biz1")
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["author"], "Alice")
        self.assertEqual(reviews[0]["rating"], 5)

    @patch("autogpt.agents.yelp_agent.openai")
    @patch("autogpt.agents.yelp_agent.requests")
    def test_summarise_reviews(self, mock_requests, mock_openai):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"reviews": [{"user": {"name": "Bob"}, "rating": 4,
                                        "text": "Good place.", "time_created": "", "url": ""}]},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Overall positive with some concerns."))]
        )
        agent = self._make_agent()
        result = agent.summarise_reviews("biz1")
        self.assertIn("reviews", result)
        self.assertIn("summary", result)
        self.assertEqual(result["summary"], "Overall positive with some concerns.")

    @patch("autogpt.agents.yelp_agent.openai")
    @patch("autogpt.agents.yelp_agent.requests")
    def test_competitor_analysis(self, mock_requests, mock_openai):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"businesses": []},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Market is fragmented."))]
        )
        agent = self._make_agent()
        result = agent.competitor_analysis("yoga studio", "Austin, TX")
        self.assertIn("businesses", result)
        self.assertIn("analysis", result)

    @patch("autogpt.agents.yelp_agent.requests")
    def test_run_routes_to_search(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"businesses": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("find Italian restaurants in Boston")
        self.assertIn("businesses", result)

    @patch("autogpt.agents.yelp_agent.openai")
    @patch("autogpt.agents.yelp_agent.requests")
    def test_run_routes_to_competitor_analysis(self, mock_requests, mock_openai):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"businesses": []},
            raise_for_status=lambda: None,
        )
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Analysis here."))]
        )
        agent = self._make_agent()
        result = agent.run("competitive analysis for yoga studios in Austin")
        self.assertIn("analysis", result)

    @patch("autogpt.agents.yelp_agent.requests")
    def test_get_reviews_sends_bearer_token(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"reviews": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        agent.get_reviews("biz1")
        headers = mock_requests.get.call_args[1]["headers"]
        self.assertIn("Bearer", headers["Authorization"])


# ======================================================================
# PinterestAgent tests
# ======================================================================

class TestPinterestAgent(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()

    def _make_agent(self):
        from autogpt.agents.pinterest_agent import PinterestAgent
        return PinterestAgent(self.cfg)

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_list_boards_returns_list(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [
                    {"id": "b1", "name": "Recipes", "description": "Food", "privacy": "PUBLIC", "pin_count": 10}
                ]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        boards = agent.list_boards()
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["name"], "Recipes")

    def test_list_boards_raises_without_token(self):
        self.cfg.pinterest_access_token = ""
        agent = self._make_agent()
        with self.assertRaises(ValueError):
            agent.list_boards()

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_create_board(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"id": "new_b", "name": "Tech Tips", "privacy": "PUBLIC"},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.create_board("Tech Tips", description="Tips for devs")
        self.assertEqual(result["id"], "new_b")
        payload = mock_requests.post.call_args[1]["json"]
        self.assertEqual(payload["name"], "Tech Tips")

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_create_pin(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"id": "pin1", "title": "My Pin"},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.create_pin(
            board_id="b1",
            title="My Pin",
            description="A great pin",
            image_url="https://example.com/img.jpg",
            link="https://example.com",
        )
        self.assertEqual(result["id"], "pin1")
        payload = mock_requests.post.call_args[1]["json"]
        self.assertEqual(payload["board_id"], "b1")
        self.assertEqual(payload["media_source"]["url"], "https://example.com/img.jpg")

    @patch("autogpt.agents.pinterest_agent.openai")
    @patch("autogpt.agents.pinterest_agent.requests")
    def test_compose_and_pin(self, mock_requests, mock_openai):
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Amazing Recipe"))]),  # title
            MagicMock(choices=[MagicMock(message=MagicMock(content="Try this delicious dish..."))]),  # desc
        ]
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"id": "pin2"},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.compose_and_pin(
            brief="Share a healthy salad recipe",
            board_id="b1",
            image_url="https://example.com/salad.jpg",
        )
        self.assertIn("title", result)
        self.assertIn("description", result)
        self.assertIn("pin", result)
        self.assertEqual(result["title"], "Amazing Recipe")

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_list_pins(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {
                "items": [{"id": "p1", "title": "Pin 1", "description": "Desc",
                           "link": "https://x.com", "created_at": "2025-01-01"}]
            },
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        pins = agent.list_pins("b1")
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0]["title"], "Pin 1")

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_run_routes_to_list_boards(self, mock_requests):
        mock_requests.get.return_value = MagicMock(
            json=lambda: {"items": []},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("show my boards on Pinterest")
        self.assertIn("boards", result)

    @patch("autogpt.agents.pinterest_agent.requests")
    def test_run_routes_to_create_board(self, mock_requests):
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"id": "b99", "name": "Travel"},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("create board Travel Inspiration")
        self.assertIn("id", result)

    @patch("autogpt.agents.pinterest_agent.openai")
    @patch("autogpt.agents.pinterest_agent.requests")
    def test_run_compose_and_pin_uses_default_board(self, mock_requests, mock_openai):
        mock_openai.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Title"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Description"))]),
        ]
        mock_requests.post.return_value = MagicMock(
            json=lambda: {"id": "pinX"},
            raise_for_status=lambda: None,
        )
        agent = self._make_agent()
        result = agent.run("Pin our new product photo https://example.com/photo.jpg")
        self.assertIn("pin", result)

    def test_run_returns_error_without_board_id(self):
        self.cfg.pinterest_default_board_id = ""
        agent = self._make_agent()
        result = agent.run("Create a pin for our new product https://example.com/img.jpg")
        self.assertIn("error", result)

    def test_run_returns_error_without_image_url(self):
        agent = self._make_agent()
        result = agent.run("Create a pin about our product launch")
        self.assertIn("error", result)


# ======================================================================
# Orchestrator routing tests for the 5 new agents
# ======================================================================

class TestOrchestratorNewChannelAgents(unittest.TestCase):
    def setUp(self):
        self.cfg = _make_config()
        self.cfg.database_url = ""

    def _make_routing(self, agent_name: str, task: str) -> str:
        return json.dumps({"agent": agent_name, "task": task, "direct_reply": ""})

    def _side_effects(self, routing_json: str) -> list:
        return [
            MagicMock(choices=[MagicMock(message=MagicMock(content=routing_json))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Done."))]),
        ]

    @patch("autogpt.orchestrator.openai")
    def test_telegram_routed(self, mock_openai):
        mock_openai.chat.completions.create.side_effect = self._side_effects(
            self._make_routing("telegram", "Announce product launch on Telegram")
        )
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.telegram_agent import TelegramAgent
        with patch.object(TelegramAgent, "run", return_value={"message": "Sent!", "api_response": {}}):
            orc = Orchestrator(self.cfg)
            orc.chat("Announce our launch on Telegram")
            self.assertEqual(orc.last_agent, "telegram")

    @patch("autogpt.orchestrator.openai")
    def test_youtube_routed(self, mock_openai):
        mock_openai.chat.completions.create.side_effect = self._side_effects(
            self._make_routing("youtube", "Search for startup pitch videos")
        )
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.youtube_agent import YouTubeAgent
        with patch.object(YouTubeAgent, "run", return_value={"videos": [], "count": 0, "summary": ""}):
            orc = Orchestrator(self.cfg)
            orc.chat("Search YouTube for startup pitch videos")
            self.assertEqual(orc.last_agent, "youtube")

    @patch("autogpt.orchestrator.openai")
    def test_google_routed(self, mock_openai):
        mock_openai.chat.completions.create.side_effect = self._side_effects(
            self._make_routing("google", "Research SaaS pricing models")
        )
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.google_agent import GoogleAgent
        with patch.object(GoogleAgent, "run", return_value={"results": [], "summary": ""}):
            orc = Orchestrator(self.cfg)
            orc.chat("Research SaaS pricing strategies on Google")
            self.assertEqual(orc.last_agent, "google")

    @patch("autogpt.orchestrator.openai")
    def test_yelp_routed(self, mock_openai):
        mock_openai.chat.completions.create.side_effect = self._side_effects(
            self._make_routing("yelp", "Find coffee shops in Austin TX")
        )
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.yelp_agent import YelpAgent
        with patch.object(YelpAgent, "run", return_value={"businesses": []}):
            orc = Orchestrator(self.cfg)
            orc.chat("Find coffee shops in Austin on Yelp")
            self.assertEqual(orc.last_agent, "yelp")

    @patch("autogpt.orchestrator.openai")
    def test_pinterest_routed(self, mock_openai):
        mock_openai.chat.completions.create.side_effect = self._side_effects(
            self._make_routing("pinterest", "List my Pinterest boards")
        )
        from autogpt.orchestrator import Orchestrator
        from autogpt.agents.pinterest_agent import PinterestAgent
        with patch.object(PinterestAgent, "run", return_value={"boards": [], "count": 0}):
            orc = Orchestrator(self.cfg)
            orc.chat("List my Pinterest boards")
            self.assertEqual(orc.last_agent, "pinterest")


if __name__ == "__main__":
    unittest.main()
