from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from organize.logger import logger

from .action import Action
from .filter import All, Any, Filter, Not
from .location import Location
from .mantle_appai.events import (
    TraceSession,
    component_evidence,
    component_inputs,
    component_name,
)
from .output import Output
from .registry import action_by_name, filter_by_name
from .resource import Resource
from .template import render
from .utils import ReportSummary
from .validators import FlatList, flatten
from .walker import Walker

FilterMode = Literal["all", "any", "none"]


def action_from_dict(d: Dict) -> Action:
    """
    :param d:
        A dict in the forms of
        { "action_name": None }
        { "action_name": "value" }
        { "action_name": {"param": "value"} }
    :returns:
        An instantiated action.
    """
    if not len(d.keys()) == 1:
        raise ValueError("Action definition must have only one key")
    name, value = next(iter(d.items()))
    ActionCls = action_by_name(name)
    if value is None:
        return ActionCls()
    elif isinstance(value, dict):
        return ActionCls(**value)
    else:
        return ActionCls(value)


def filter_from_dict(d: Dict) -> Filter:
    """
    :param d:
        A dict in the forms of ("not" prefix is optional)
        { "[not] filter_name": None }
        { "[not] filter_name": "value" }
        { "[not] filter_name": {"param": "value"} }
    :returns: An instantiated filter.
    """
    if not len(d.keys()) == 1:
        raise ValueError("Filter definition must have a single key")
    name, value = next(iter(d.items()))

    # check for "not" in filter key
    invert_filter = False
    if name.startswith("not "):
        name = name[4:]
        invert_filter = True

    FilterCls = filter_by_name(name)

    # instantiate
    if value is None:
        inst = FilterCls()
    elif isinstance(value, dict):
        inst = FilterCls(**value)
    else:
        inst = FilterCls(value)

    return Not(inst) if invert_filter else inst


def filter_pipeline(
    filters: Iterable[Filter],
    filter_mode: FilterMode,
    res: Resource,
    output: Output,
    trace: Optional[TraceSession] = None,
) -> bool:
    collection: "All | Any"
    if filter_mode == "all":
        collection = All(*filters)
    elif filter_mode == "any":
        collection = Any(*filters)
    elif filter_mode == "none":
        collection = All(*[Not(x) for x in filters])
    else:
        raise ValueError(f"Unknown filter mode {filter_mode}")
    if trace is None or not trace.enabled:
        return collection.pipeline(res, output=output)

    rule_name = res.rule.name if res.rule and res.rule.name else f"rule {res.rule_nr + 1}"
    evaluated = 0
    result = False if filter_mode == "any" else True
    pipeline_filters = list(collection.filters)
    for filter_item in pipeline_filters:
        name = component_name(filter_item, "filter")
        evaluated += 1
        try:
            with trace.component("filter", name):
                matched = filter_item.pipeline(res, output=output)
            trace.emit(
                stage="filter_evaluation",
                component_type="filter",
                component_name=name,
                outcome="matched" if matched else "not_matched",
                reason_code="filter_matched" if matched else "filter_not_matched",
                explanation=(
                    f'Filter "{name}" matched the resource.'
                    if matched
                    else f'Filter "{name}" did not match the resource.'
                ),
                rule_name=rule_name,
                resource_path=res.path,
                evidence={
                    "filter_mode": filter_mode,
                    "result": matched,
                    **component_evidence(filter_item, res.vars),
                },
                inputs=component_inputs(filter_item),
                outputs={"resource_vars": res.vars},
            )
        except Exception as error:
            output.msg(res=res, level="error", msg=str(error), sender=filter_item)
            logger.exception(error)
            trace.emit(
                stage="filter_evaluation",
                component_type="filter",
                component_name=name,
                outcome="failed",
                reason_code="filter_exception",
                explanation=str(error),
                rule_name=rule_name,
                resource_path=res.path,
                evidence={"exception_type": type(error).__name__},
                inputs=component_inputs(filter_item),
            )
            matched = False

        if filter_mode == "any":
            result = result or matched
        else:
            result = result and matched
            if not result:
                break

    trace.emit(
        stage="filter_pipeline",
        component_type="pipeline",
        component_name=filter_mode,
        outcome="matched" if result else "not_matched",
        reason_code="filter_pipeline_passed" if result else "filter_pipeline_rejected",
        explanation=(
            "The resource passed the filter pipeline."
            if result
            else "The resource was rejected by the filter pipeline."
        ),
        rule_name=rule_name,
        resource_path=res.path,
        evidence={
            "filter_mode": filter_mode,
            "evaluated_filters": evaluated,
            "configured_filters": len(pipeline_filters),
        },
    )
    return result


def action_pipeline(
    actions: Iterable[Action],
    res: Resource,
    simulate: bool,
    output: Output,
    trace: Optional[TraceSession] = None,
) -> Iterable[Action]:
    for action in actions:
        name = component_name(action, "action")
        rule_name = res.rule.name if res.rule and res.rule.name else f"rule {res.rule_nr + 1}"
        try:
            yield action
            if trace is not None:
                trace.emit(
                    stage="action_planning",
                    component_type="action",
                    component_name=name,
                    outcome="planned",
                    reason_code="action_planned",
                    explanation=f'Action "{name}" is next in execution order.',
                    rule_name=rule_name,
                    resource_path=res.path,
                    inputs=component_inputs(action),
                )
            if trace is not None:
                with trace.component("action", name):
                    action.pipeline(res=res, simulate=simulate, output=output)
            else:
                action.pipeline(res=res, simulate=simulate, output=output)
            if trace is not None:
                ran_in_simulation = bool(getattr(action, "run_in_simulation", False))
                executed = not simulate or ran_in_simulation
                trace.emit(
                    stage="action_execution",
                    component_type="action",
                    component_name=name,
                    outcome="executed" if executed else "skipped",
                    reason_code=(
                        "action_executed"
                        if executed
                        else "action_suppressed_by_simulation"
                    ),
                    explanation=(
                        f'Action "{name}" executed.'
                        if executed
                        else f'Action "{name}" was simulated; mutation was suppressed.'
                    ),
                    rule_name=rule_name,
                    resource_path=res.path,
                    evidence={"run_in_simulation": ran_in_simulation},
                    outputs={"resource_vars": res.vars},
                )
        except StopIteration:
            if trace is not None:
                trace.emit(
                    stage="action_execution",
                    component_type="action",
                    component_name=name,
                    outcome="skipped",
                    reason_code="action_stopped_pipeline",
                    explanation=f'Action "{name}" stopped the remaining action pipeline.',
                    rule_name=rule_name,
                    resource_path=res.path,
                )
            break
        except Exception as error:
            if trace is not None:
                trace.emit(
                    stage="action_execution",
                    component_type="action",
                    component_name=name,
                    outcome="failed",
                    reason_code="action_exception",
                    explanation=str(error),
                    rule_name=rule_name,
                    resource_path=res.path,
                    evidence={"exception_type": type(error).__name__},
                )
            raise


class Rule(BaseModel):
    name: Optional[str] = None
    enabled: bool = True
    targets: Literal["files", "dirs"] = "files"
    locations: FlatList[Location] = Field(default_factory=list)
    subfolders: bool = False
    tags: Set[str] = Field(default_factory=set)
    filters: List[Filter] = Field(default_factory=list)
    filter_mode: FilterMode = "all"
    actions: List[Action] = Field(..., min_length=1)

    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    @field_validator("locations", mode="before")
    def validate_locations(cls, locations):
        if locations is None:
            return []
        locations = flatten(locations)
        result = []
        for x in locations:
            if isinstance(x, str):
                x = {"path": x}
            result.append(x)
        return result

    @field_validator("filters", mode="before")
    def validate_filters(cls, filters):
        result = []
        filters = flatten(filters)
        for x in filters:
            # make sure "- extension" becomes "- extension:"
            if isinstance(x, str):
                x = {x: None}
            # create instance from dict
            if isinstance(x, dict):
                result.append(filter_from_dict(x))
            # other instances
            else:
                result.append(x)
        return result

    @field_validator("actions", mode="before")
    def validate_actions(cls, actions):
        result = []
        actions = flatten(actions)
        for x in actions:
            # make sure "- extension" becomes "- extension:"
            if isinstance(x, str):
                x = {x: None}
            # create instance from dict
            if isinstance(x, dict):
                result.append(action_from_dict(x))
            # other instances
            else:
                result.append(x)
        return result

    @model_validator(mode="after")
    def validate_target_support(self) -> "Rule":
        # standalone mode
        if not self.locations:
            if self.filters:
                raise ValueError("Filters are present but no locations are given!")
            for action in self.actions:
                if not action.action_config.standalone:
                    raise ValueError(
                        f'Action "{action.action_config.name}" does not support '
                        "standalone mode (no rule.locations specified)."
                    )
        # targets dirs
        if self.targets == "dirs":
            for filter in self.filters:
                if not filter.filter_config.dirs:
                    raise ValueError(
                        f'Filter "{filter.filter_config.name}" does not support '
                        "folders (targets: dirs)"
                    )
            for action in self.actions:
                if not action.action_config.dirs:
                    raise ValueError(
                        f'Action "{action.action_config.name}" does not support '
                        "folders (targets: dirs)"
                    )
        # targets files
        elif self.targets == "files":
            for filter in self.filters:
                if not filter.filter_config.files:
                    raise ValueError(
                        f'Filter "{filter.filter_config.name}" does not support '
                        "files (targets: files)"
                    )
            for action in self.actions:
                if not action.action_config.files:
                    raise ValueError(
                        f'Action "{action.action_config.name}" does not support '
                        "files (targets: files)"
                    )
        else:
            raise ValueError(f"Unknown target: {self.targets}")

        return self

    def walk(self, rule_nr: int = 0, trace: Optional[TraceSession] = None):
        rule_name = self.name or f"rule {rule_nr + 1}"
        for location in self.locations:
            # instantiate the filesystem walker
            exclude_files = location.system_exclude_files | location.exclude_files
            exclude_dirs = location.system_exclude_dirs | location.exclude_dirs
            if location.max_depth == "inherit":
                max_depth = None if self.subfolders else 0
            else:
                max_depth = location.max_depth

            walker = Walker(
                min_depth=location.min_depth,
                max_depth=max_depth,
                filter_dirs=location.filter_dirs,
                filter_files=location.filter,
                method="breadth",
                exclude_dirs=exclude_dirs,
                exclude_files=exclude_files,
            )

            # whether to walk dirs or files
            _walk_funcs = {
                "files": walker.files,
                "dirs": walker.dirs,
            }
            for loc_path in location.path:
                if trace is not None:
                    with trace.component("location", "path"):
                        expanded_path = render(loc_path)
                else:
                    expanded_path = render(loc_path)
                expanded = Path(expanded_path)
                if trace is not None:
                    exists = expanded.exists()
                    trace.emit(
                        stage="location_expansion",
                        component_type="location",
                        component_name="path",
                        outcome="entered" if exists else "failed",
                        reason_code="location_expanded" if exists else "location_missing",
                        explanation=(
                            "The location was expanded and exists."
                            if exists
                            else "The expanded location does not exist."
                        ),
                        rule_name=rule_name,
                        resource_path=expanded,
                        inputs={"configured_path": loc_path},
                        outputs={"expanded_path": expanded},
                    )
                for path in _walk_funcs[self.targets](expanded_path):
                    resource = Resource(
                        path=Path(path),
                        basedir=Path(expanded_path),
                        rule=self,
                        rule_nr=rule_nr,
                    )
                    if trace is not None:
                        trace.emit(
                            stage="target_selection",
                            component_type="target",
                            component_name=self.targets,
                            outcome="entered",
                            reason_code="target_selected",
                            explanation=f"The resource has the configured target type ({self.targets}).",
                            rule_name=rule_name,
                            resource_path=resource.path,
                            evidence={"targets": self.targets},
                        )
                    yield resource

    def execute(
        self,
        *,
        simulate: bool,
        output: Output,
        rule_nr: int = 0,
        trace: Optional[TraceSession] = None,
    ) -> ReportSummary:
        if not self.enabled:
            return ReportSummary()

        current_action: Optional[Action] = None

        # standalone mode
        if not self.locations:
            res = Resource(path=None, rule_nr=rule_nr)
            try:
                for current_action in action_pipeline(
                    actions=self.actions,
                    res=res,
                    simulate=simulate,
                    output=output,
                    trace=trace,
                ):
                    pass
                return ReportSummary(success=1)
            except Exception as e:
                output.msg(
                    res=res,
                    msg=str(e),
                    level="error",
                    sender="rule" if current_action is None else current_action,
                )
                logger.exception(e)
                return ReportSummary(errors=1)

        # normal mode
        summary = ReportSummary()
        skip_pathes: Set[Path] = set()
        for res in self.walk(rule_nr=rule_nr, trace=trace):
            if res.path in skip_pathes:
                if trace is not None:
                    trace.emit(
                        stage="target_selection",
                        component_type="resource",
                        component_name="walker_skip",
                        outcome="skipped",
                        reason_code="resource_skipped_after_prior_action",
                        explanation="A prior action marked this path to be skipped.",
                        rule_name=self.name or f"rule {rule_nr + 1}",
                        resource_path=res.path,
                    )
                continue
            result = filter_pipeline(
                filters=self.filters,
                filter_mode=self.filter_mode,
                res=res,
                output=output,
                trace=trace,
            )
            if result:
                current_action = None
                try:
                    for current_action in action_pipeline(
                        actions=self.actions,
                        res=res,
                        simulate=simulate,
                        output=output,
                        trace=trace,
                    ):
                        pass
                    skip_pathes = skip_pathes.union(res.walker_skip_pathes)
                    summary.success += 1
                except Exception as e:
                    output.msg(
                        res=res,
                        msg=str(e),
                        level="error",
                        sender="rule" if current_action is None else current_action,
                    )
                    logger.exception(e)
                    summary.errors += 1
        return summary
