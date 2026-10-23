from __future__ import annotations

import os
import textwrap
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Union

import yaml
from pydantic import ConfigDict, ValidationError
from pydantic.dataclasses import dataclass

from .errors import ConfigError
from .output import Default, Output
from .rule import Rule
from .template import render
from .utils import ReportSummary, normalize_unicode

if TYPE_CHECKING:
    from .mantle_appai.events import TraceSession

Tags = Iterable[str]


def default_yaml_cnst(loader, tag_suffix, node):
    # disable yaml constructors for strings starting with exclamation marks
    # https://stackoverflow.com/a/13281292/300783
    return str(node.tag)


yaml.add_multi_constructor("", default_yaml_cnst, Loader=yaml.SafeLoader)


def should_execute(rule_tags: Tags, tags: Tags, skip_tags: Tags) -> bool:
    """
    returns whether the rule with `rule_tags` should be executed,
    given `tags` and `skip_tags`
    """
    if not rule_tags:
        rule_tags = set()
    if not tags:
        tags = set()
    if not skip_tags:
        skip_tags = set()

    if "always" in rule_tags and "always" not in skip_tags:
        return True
    if "never" in rule_tags and "never" not in tags:
        return False
    if not tags and not skip_tags:
        return True
    if not rule_tags and tags:
        return False
    should_run = any(tag in tags for tag in rule_tags) or not tags or not rule_tags
    should_skip = any(tag in skip_tags for tag in rule_tags)
    return should_run and not should_skip


@dataclass(config=ConfigDict(extra="ignore"))
class Config:
    rules: List[Rule]

    _config_path: Optional[Path] = None

    @classmethod
    def from_string(cls, config: str, config_path: Optional[Path] = None) -> Config:
        normalized = normalize_unicode(config)
        dedented = textwrap.dedent(normalized)
        as_dict = yaml.load(dedented, Loader=yaml.SafeLoader)
        try:
            if not as_dict:
                raise ValueError("Config is empty")
            inst = cls(**as_dict)
            inst._config_path = config_path
            return inst
        except ValidationError as e:
            # add a config_path property to the ValidationError
            raise ConfigError(e=e, config_path=config_path) from e

    @classmethod
    def from_path(cls, config_path: Path) -> Config:
        text = config_path.read_text(encoding="utf-8")
        inst = cls.from_string(text, config_path=config_path)
        return inst

    def execute(
        self,
        simulate: bool = True,
        output: Output = Default(),
        tags: Tags = set(),
        skip_tags: Tags = set(),
        working_dir: Union[str, Path] = ".",
        trace: Optional[TraceSession] = None,
    ) -> None:
        activation = trace.activate() if trace is not None else nullcontext()
        with activation:
            working_path = Path(render(str(working_dir)))
            if trace is not None:
                trace.emit(
                    stage="working_directory",
                    component_type="configuration",
                    component_name="working_directory",
                    outcome="entered",
                    reason_code="working_directory_resolved",
                    explanation="The configured working directory was resolved.",
                    inputs={"working_dir": str(working_dir)},
                    outputs={"working_path": working_path},
                )
            os.chdir(working_path)
            output.start(
                simulate=simulate,
                config_path=self._config_path,
                working_dir=working_path,
            )
            summary = ReportSummary()
            try:
                for rule_nr, rule in enumerate(self.rules):
                    selected = should_execute(
                        rule_tags=rule.tags,
                        tags=tags,
                        skip_tags=skip_tags,
                    )
                    rule_name = rule.name or f"rule {rule_nr + 1}"
                    if trace is not None:
                        if not rule.enabled:
                            reason = "rule_disabled"
                            explanation = f'Rule "{rule_name}" is disabled.'
                        elif selected:
                            reason = "rule_selected"
                            explanation = f'Rule "{rule_name}" is eligible for this run.'
                        else:
                            reason = "rule_excluded_by_tags"
                            explanation = f'Rule "{rule_name}" was excluded by tag selection.'
                        trace.emit(
                            stage="rule_selection",
                            component_type="rule",
                            component_name=rule_name,
                            outcome="entered" if selected and rule.enabled else "skipped",
                            reason_code=reason,
                            explanation=explanation,
                            rule_name=rule_name,
                            evidence={
                                "enabled": rule.enabled,
                                "rule_tags": sorted(rule.tags),
                                "included_tags": sorted(tags),
                                "skipped_tags": sorted(skip_tags),
                            },
                        )
                    if selected:
                        rule_summary = rule.execute(
                            simulate=simulate,
                            output=output,
                            rule_nr=rule_nr,
                            trace=trace,
                        )
                        summary += rule_summary
            finally:
                output.end(summary.success, summary.errors)
