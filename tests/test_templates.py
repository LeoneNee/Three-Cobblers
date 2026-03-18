import pytest
from consensus_engine.templates import build_proposal_prompt, build_review_prompt, build_synthesis_prompt


class TestBuildProposalPrompt:
    def test_contains_task_and_content(self):
        system, user = build_proposal_prompt(
            task="设计登录模块",
            content="现有 Flask 应用",
            scene="planning",
        )
        assert "设计登录模块" in user
        assert "现有 Flask 应用" in user
        assert "planning" in user

    def test_system_prompt_is_expert(self):
        system, _ = build_proposal_prompt("t", "c", "review")
        assert "专家" in system or "expert" in system.lower()


class TestBuildReviewPrompt:
    def test_contains_proposals(self):
        proposals = {"modelA": "方案A内容", "modelB": "方案B内容"}
        system, user = build_review_prompt(
            task="设计登录模块",
            proposals=proposals,
        )
        assert "方案A内容" in user
        assert "方案B内容" in user
        assert "modelA" in user

    def test_system_prompt_is_reviewer(self):
        system, _ = build_review_prompt("t", {"a": "b"})
        assert "评审" in system or "review" in system.lower()


class TestBuildSynthesisPrompt:
    def test_contains_proposals_and_reviews(self):
        proposals = {"modelA": "方案A"}
        reviews = {"modelB": "评审意见B"}
        system, user = build_synthesis_prompt(
            task="设计登录模块",
            proposals=proposals,
            reviews=reviews,
        )
        assert "方案A" in user
        assert "评审意见B" in user

    def test_system_prompt_is_judge(self):
        system, _ = build_synthesis_prompt("t", {"a": "b"}, {"c": "d"})
        assert "裁判" in system or "judge" in system.lower()
