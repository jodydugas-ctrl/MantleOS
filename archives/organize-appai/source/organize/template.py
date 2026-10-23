import os
from datetime import date, datetime
from typing import Union

import jinja2

# variables that should be always available in a template
BASIC_VARS = dict(
    env=os.environ,
    now=datetime.now,
    utcnow=datetime.utcnow,
    today=date.today,
)


def finalize_placeholder(x):
    # This is used to make the `path` arg available in the filters and actions.
    # If a template uses `path` where no syspath is available this makes it possible
    # to raise an exception.
    if isinstance(x, Exception):
        raise x
    return x


Template = jinja2.Environment(
    variable_start_string="{",
    variable_end_string="}",
    autoescape=False,
    finalize=finalize_placeholder,
    undefined=jinja2.StrictUndefined,
)


def render(template: Union[str, jinja2.Template], args=None) -> str:
    if args is None:
        args = dict()
    try:
        if isinstance(template, jinja2.Template):
            text = template.render(**args, **BASIC_VARS)
        else:
            text = Template.from_string(template).render(**args, **BASIC_VARS)
    except jinja2.UndefinedError as e:
        msg = f"Missing value for template: {e}. Maybe you forgot a filter?"
        error = ValueError(msg)
        _trace_template(template=template, rendered=None, error=error)
        raise error from e

    # expand user and fill environment vars
    text = os.path.expanduser(text)
    text = os.path.expandvars(text)
    _trace_template(template=template, rendered=text, error=None)
    return text


def _trace_template(template, rendered, error) -> None:
    """Emit optional trace evidence without coupling normal rendering to AppAI."""

    try:
        from organize.mantle_appai.events import emit_template_resolution

        emit_template_resolution(template=template, rendered=rendered, error=error)
    except Exception:
        return None
