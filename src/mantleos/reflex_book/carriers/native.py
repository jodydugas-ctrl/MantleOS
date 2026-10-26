"""Experimental REFLEX adapter to public, opaque MantleOS Body attachments."""
import hashlib
from pathlib import Path

from mantleos import attachments
from mantleos.transactions import atomic_bytes, body_lock, ensure_clean
from .raw import RawCarrier
from .contract import MAX_CARRIER_BYTES

MEDIA_TYPE = 'application/vnd.mantle.reflex-raw'


def attach(body, envelope, *, expected_program_sha256, output):
    """Validate a candidate as data, then publish a separate Body snapshot."""
    verification = RawCarrier().verify(envelope, expected_program_sha256)
    result = attachments.add(body, envelope, media_type=MEDIA_TYPE,
                             expected_sha256=hashlib.sha256(envelope).hexdigest(), output=output)
    return {**result, 'reflex': verification}


def extract(body, *, attachment_sha256, expected_program_sha256, output):
    """Verify both digest layers before exclusive publication of the raw envelope."""
    body, output = Path(body).resolve(), Path(output).resolve()
    if output.is_relative_to(body):
        raise ValueError('Extraction output must be outside Body')
    with body_lock(body):
        ensure_clean(body)
        listing = attachments.inspect(body)
        entry = next((i for i in listing['attachments'] if i['sha256'] == attachment_sha256), None)
        if entry is None or entry['media_type'] != MEDIA_TYPE or entry['bytes'] > MAX_CARRIER_BYTES:
            raise ValueError('Unknown REFLEX raw attachment')
        envelope = (body / entry['path']).read_bytes()
        verification = RawCarrier().verify(envelope, expected_program_sha256)
        atomic_bytes(output, envelope, replace=False)
        return {**verification, 'attachment_sha256': attachment_sha256, 'output': str(output)}
