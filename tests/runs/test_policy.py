"""Opposed contract tests for the R2 execution policy evaluator."""
from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.runs.policy import Decision, Effect, EffectKind, ExecutionPolicy, PolicyRule


def test_default_trust_mode_allows_reads_and_asks_writes():
    policy = ExecutionPolicy.from_trust_mode("default")
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "read")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write")) == Decision.ASK
    assert policy.evaluate(Effect(EffectKind.NETWORK, "connect")) == Decision.ASK


def test_strict_trust_mode_denies_by_default():
    policy = ExecutionPolicy.from_trust_mode("strict")
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "read")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write")) == Decision.DENY
    assert policy.evaluate(Effect(EffectKind.NETWORK, "connect")) == Decision.DENY


def test_permissive_trust_mode_allows_by_default():
    policy = ExecutionPolicy.from_trust_mode("permissive")
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.NETWORK, "connect")) == Decision.ALLOW


def test_rule_path_matches_prefix_and_glob():
    policy = ExecutionPolicy(
        trust_mode="default",
        default_decision=Decision.DENY,
        rules=[
            PolicyRule(
                kind=EffectKind.FILESYSTEM,
                action="write",
                path="/workspace/src",
                decision=Decision.ALLOW,
            ),
            PolicyRule(
                kind=EffectKind.FILESYSTEM,
                action="read",
                path="/workspace/*.txt",
                decision=Decision.ALLOW,
            ),
        ],
    )
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write", "/workspace/src/foo.py")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write", "/workspace/tmp")) == Decision.DENY
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "read", "/workspace/readme.txt")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "read", "/workspace/src/foo.py")) == Decision.DENY


def test_rule_matches_target_and_action():
    policy = ExecutionPolicy(
        trust_mode="default",
        default_decision=Decision.ASK,
        rules=[
            PolicyRule(
                kind=EffectKind.NETWORK,
                action="connect",
                target="api.github.com",
                decision=Decision.ALLOW,
            ),
        ],
    )
    assert policy.evaluate(Effect(EffectKind.NETWORK, "connect", target="api.github.com")) == Decision.ALLOW
    assert policy.evaluate(Effect(EffectKind.NETWORK, "connect", target="evil.com")) == Decision.ASK


def test_policy_serialization_roundtrip():
    policy = ExecutionPolicy.from_trust_mode("default")
    restored = ExecutionPolicy.from_json(policy.to_json())
    assert restored.trust_mode == policy.trust_mode
    assert restored.default_decision == policy.default_decision
    assert len(restored.rules) == len(policy.rules)


def test_unknown_trust_mode_falls_back_to_default():
    policy = ExecutionPolicy.from_trust_mode("unknown")
    assert policy.trust_mode == "default"
    assert policy.default_decision == Decision.ASK


def test_path_traversal_outside_rule_path_is_denied():
    policy = ExecutionPolicy(
        trust_mode="default",
        default_decision=Decision.DENY,
        rules=[
            PolicyRule(
                kind=EffectKind.FILESYSTEM,
                action="write",
                path="/workspace",
                decision=Decision.ALLOW,
            ),
        ],
    )
    assert policy.evaluate(Effect(EffectKind.FILESYSTEM, "write", "/workspace/../etc/passwd")) == Decision.DENY
