from __future__ import annotations

import filecmp
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NamedTuple

from organize.output import Output
from organize.resource import Resource
from organize.template import render
from organize.mantle_appai.events import emit_conflict

if TYPE_CHECKING:
    from jinja2 import Template

# TODO: keep_newer, keep_older, keep_bigger, keep_smaller
ConflictMode = Literal[
    "skip", "overwrite", "deduplicate", "trash", "rename_new", "rename_existing"
]


class ConflictResult(NamedTuple):
    skip_action: bool  # Whether to skip the current action
    use_dst: Path  # The Path to continue with


def next_free_name(dst: Path, template: Template) -> Path:
    """
    Increments {counter} in the template until the given resource does not exist.

    Attributes:
        dst (Path):
            The destination path.
        template (jinja2.Template):
            A jinja2 template with placeholders for {name}, {extension} and {counter}

    Raises:
        ValueError if no free name can be found with the given template.

    Returns:
        (Path) A path according to the given template that does not exist.
    """
    if not dst.exists():
        return dst
    counter = 2
    prev_candidate = None
    while True:
        args = dict(
            name=dst.stem,
            extension=dst.suffix,
            counter=counter,
        )
        new_name = render(template, args)
        candidate = dst.with_name(new_name)
        if not candidate.exists():
            return candidate
        if prev_candidate == candidate:
            raise ValueError(
                "Could not find a free filename for the given template. "
                'Maybe you forgot the "{counter}" placeholder?'
            )
        prev_candidate = candidate
        counter += 1


def resolve_conflict(
    dst: Path,
    res: Resource,
    conflict_mode: ConflictMode,
    rename_template: Template,
    simulate: bool,
    output: Output,
) -> ConflictResult:
    """
    Handle a conflict if `dst` already exists.
    """
    assert res.path is not None

    # no conflict, just continue with the action.
    if not dst.exists():
        return ConflictResult(skip_action=False, use_dst=dst)

    def _print(msg: str):
        output.msg(res=res, sender="conflict", msg=msg)

    _print(f'"{dst}" already exists! (Conflict mode is "{conflict_mode}")')

    if res.path.resolve() == dst.resolve():
        _print("Same resource: Skipped.")
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="skipped",
            reason_code="conflict_same_resource",
            explanation="Source and destination resolve to the same resource.",
            use_destination=res.path,
        )
        return ConflictResult(skip_action=True, use_dst=res.path)

    if conflict_mode == "trash":
        _print(f'Trash "{dst}"')
        if not simulate:
            from organize.actions.trash import trash

            trash(path=dst)
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="planned" if simulate else "executed",
            reason_code="conflict_destination_trashed",
            explanation="The existing destination is trashed before continuing.",
            use_destination=dst,
        )
        return ConflictResult(skip_action=False, use_dst=dst)

    elif conflict_mode == "skip":
        _print("Skipped.")
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="skipped",
            reason_code="conflict_skipped",
            explanation="The conflict policy skips this action.",
            use_destination=res.path,
        )
        return ConflictResult(skip_action=True, use_dst=res.path)

    elif conflict_mode == "overwrite":
        _print(f"Overwriting {dst}.")
        if not simulate:
            from organize.actions.delete import delete

            delete(path=dst)
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="planned" if simulate else "executed",
            reason_code="conflict_overwrite",
            explanation="The existing destination is removed before continuing.",
            use_destination=dst,
        )
        return ConflictResult(skip_action=False, use_dst=dst)

    elif conflict_mode == "deduplicate":
        if filecmp.cmp(res.path, dst, shallow=True):
            _print("Duplicate skipped.")
            emit_conflict(
                resource_path=res.path,
                destination=dst,
                mode=conflict_mode,
                outcome="skipped",
                reason_code="conflict_duplicate_skipped",
                explanation="Source and destination compare equal, so the duplicate is skipped.",
                use_destination=res.path,
            )
            return ConflictResult(skip_action=True, use_dst=res.path)
        else:
            new_path = next_free_name(
                dst=dst,
                template=rename_template,
            )
            emit_conflict(
                resource_path=res.path,
                destination=dst,
                mode=conflict_mode,
                outcome="conflict",
                reason_code="conflict_deduplicate_renamed",
                explanation="Resources differ; a free destination name was selected.",
                use_destination=new_path,
            )
            return ConflictResult(skip_action=False, use_dst=new_path)

    elif conflict_mode == "rename_new":
        new_path = next_free_name(
            dst=dst,
            template=rename_template,
        )
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="conflict",
            reason_code="conflict_renamed_new",
            explanation="A free name was selected for the incoming resource.",
            use_destination=new_path,
        )
        return ConflictResult(skip_action=False, use_dst=new_path)

    elif conflict_mode == "rename_existing":
        new_path = next_free_name(
            dst=dst,
            template=rename_template,
        )
        _print('Renaming existing to: "{new_path.name}"')
        if not simulate:
            dst.rename(new_path)
        emit_conflict(
            resource_path=res.path,
            destination=dst,
            mode=conflict_mode,
            outcome="planned" if simulate else "executed",
            reason_code="conflict_renamed_existing",
            explanation="The existing destination is renamed to a free name.",
            use_destination=dst,
        )
        return ConflictResult(skip_action=False, use_dst=dst)

    raise ValueError("Unknown conflict_mode %s" % conflict_mode)
