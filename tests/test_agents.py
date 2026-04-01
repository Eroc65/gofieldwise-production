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
            reply = ws.receive_text()
        self.assertEqual(reply, "WS reply!")

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
            r1 = ws.receive_text()
            ws.send_text("Message two")
            r2 = ws.receive_text()

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


if __name__ == "__main__":
    unittest.main()

