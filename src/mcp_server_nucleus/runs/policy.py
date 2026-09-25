"""Typed execution policy and effect evaluation for Nucleus Renaissance runs."""
from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePath
from typing import Any


class EffectKind(str, Enum):
    """Categories of side-effect a runner may request."""

    FILESYSTEM = "filesystem"
    NETWORK = "network"
    PROCESS = "process"
    SECRET = "secret"
    EXTERNAL = "external"


class Decision(str, Enum):
    """Policy decision for a requested effect."""

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class Effect:
    """A concrete side-effect requested by a runner or tool call."""

    kind: EffectKind
    action: str
    path: str | None = None
    target: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyRule:
    """A single allow/ask/deny rule matched against an :class:`Effect`."""

    kind: EffectKind | None = None
    action: str | None = None
    path: str | None = None
    target: str | None = None
    decision: Decision = Decision.ASK

    def matches(self, effect: Effect) -> bool:
        if self.kind is not None and self.kind != effect.kind:
            return False
        if self.action is not None and self.action != effect.action:
            return False
        if self.target is not None and self.target != effect.target:
            return False
        if self.path is not None:
            if effect.path is None:
                return False
            try:
                effect_p = PurePath(os.path.normpath(effect.path))
                rule_p = PurePath(os.path.normpath(self.path))
            except (ValueError, TypeError):
                return False
            if not effect_p.is_relative_to(rule_p) and not fnmatch.fnmatch(str(effect_p), str(rule_p)):
                return False
        return True


@dataclass
class ExecutionPolicy:
    """A runnable policy: trust mode, rule list, and per-domain defaults."""

    trust_mode: str = "default"
    default_decision: Decision = Decision.ASK
    rules: list[PolicyRule] = field(default_factory=list)
    network_policy: dict[str, Any] = field(default_factory=dict)
    process_policy: dict[str, Any] = field(default_factory=dict)
    filesystem_policy: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_trust_mode(cls, trust_mode: str) -> ExecutionPolicy:
        """Return the canonical policy for a named trust mode."""
        if trust_mode == "strict":
            return cls(
                trust_mode="strict",
                default_decision=Decision.DENY,
                rules=[
                    PolicyRule(
                        kind=EffectKind.FILESYSTEM,
                        action="read",
                        decision=Decision.ALLOW,
                    ),
                ],
            )
        if trust_mode == "permissive":
            return cls(
                trust_mode="permissive",
                default_decision=Decision.ALLOW,
                rules=[],
            )
        return cls(
            trust_mode="default",
            default_decision=Decision.ASK,
            rules=[
                PolicyRule(
                    kind=EffectKind.FILESYSTEM,
                    action="read",
                    decision=Decision.ALLOW,
                ),
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_mode": self.trust_mode,
            "default_decision": self.default_decision.value,
            "rules": [
                {
                    "kind": r.kind.value if r.kind else None,
                    "action": r.action,
                    "path": r.path,
                    "target": r.target,
                    "decision": r.decision.value,
                }
                for r in self.rules
            ],
            "network_policy": self.network_policy,
            "process_policy": self.process_policy,
            "filesystem_policy": self.filesystem_policy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionPolicy:
        rules = [
            PolicyRule(
                kind=EffectKind(r["kind"]) if r.get("kind") else None,
                action=r.get("action"),
                path=r.get("path"),
                target=r.get("target"),
                decision=Decision(r.get("decision", "ask")),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            trust_mode=data.get("trust_mode", "default"),
            default_decision=Decision(data.get("default_decision", "ask")),
            rules=rules,
            network_policy=data.get("network_policy", {}),
            process_policy=data.get("process_policy", {}),
            filesystem_policy=data.get("filesystem_policy", {}),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> ExecutionPolicy:
        return cls.from_dict(json.loads(json_str))

    def evaluate(self, effect: Effect) -> Decision:
        """Return the first matching rule's decision, or the default."""
        for rule in self.rules:
            if rule.matches(effect):
                return rule.decision
        return self.default_decision


class PolicyEvaluator:
    """Thin wrapper around :class:`ExecutionPolicy` for explicit evaluation."""

    def __init__(self, policy: ExecutionPolicy) -> None:
        self._policy = policy

    def evaluate(self, effect: Effect) -> Decision:
        return self._policy.evaluate(effect)
