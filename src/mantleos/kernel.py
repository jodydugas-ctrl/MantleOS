"""Kernel/output ABI; each kernel defines its own smallest organism unit.

Cartridge is the default transport. ChromaMem/5 is the optical transport.
Both preserve the same birth, Anchor language, capability checks and Engram ledger.
Kernel-produced CELLs may be pixels or append segments. They supply no authority.
"""

FORMATS = {
    'cartridge': {'carrier':'vcw/1', 'suffixes':['.vcw','.zip'], 'default':True,
                  'read_policy':'VERIFY_BEFORE_USE'},
    'chroma': {'carrier':'ChromaMem/5', 'suffixes':['.png'], 'default':False,
               'read_policy':'VERIFY_THEN_EXPLICIT_EXTRACT;NEVER_EXECUTE_IMAGE'},
}


def formats():
    return {'schema':'mantle.kernel-formats/1','default':'cartridge',
            'thought_language':'anchor.coding.conversation/1.1',
            'shared_organs':['neural','memory','immune','metabolism','expression'],
            'formats':FORMATS,
            'cell_kernels': {'chroma.rgb/1': 'pixel', 'tape.segment/1': 'appended-record'}}


def produce_cell(kernel, payload):
    from .cells import produce
    return produce(kernel, payload)


def scan(operation, arguments, *, body=None, permit=False):
    """Coordinate native Metabolism through the established checked-action ABI.

    Operator diagnostics do not append to Engram. Explicit retention remains in
    organs.invoke/memory admission. Existing Bodies must declare each interface;
    installation never occurs implicitly during analysis.
    """
    from pathlib import Path
    import uuid
    from . import organs,cartridge
    from .effects import CheckedActionExecutor
    from .scan.service import CAPABILITIES
    from .transactions import body_lock,ensure_clean
    if operation not in {*CAPABILITIES,'scan.inspect','scan.compact','scan.experiment'}:
        raise ValueError('Unknown native SCAN operation')
    if type(permit) is not bool: raise ValueError('SCAN permission must be boolean')
    def checked(registry):
        executor = CheckedActionExecutor(registry,lambda authority,name:permit)
        result = executor.execute(operation,arguments,request_id=uuid.uuid4().hex)
        if result['stage'] == 'FAILED' and result['trace'][-1].get('reason') == 'authority_denied':
            raise PermissionError('Native SCAN requires explicit operator permission')
        if result['stage'] != 'VERIFIED':
            raise ValueError(result['trace'][-1].get('error','Native SCAN verification failed'))
        return result
    if body is None: return checked(organs.registry(Path('.'),constructing=True))
    body = Path(body).resolve()
    with body_lock(body):
        ensure_clean(body); cartridge.verify(body)
        if organs.load(body / 'BIRTH.json')['distribution']['role'] == 'reference':
            raise PermissionError('Clone the reference before operation')
        return checked(organs.system_registry(body).capability_registry())


def format_name(name):
    if name not in FORMATS:
        raise ValueError('Unsupported kernel output format (cartridge or chroma)')
    return name


def pack_verified_body(body, output, *, format='cartridge'):
    """Expression organ's sole final serializer. Caller stages immutable snapshot."""
    format_name(format)
    if format=='cartridge':
        from . import cartridge
        return cartridge.pack(body,output)
    from . import chromamem
    return chromamem.export_body(body,output)


def verify_restored_output(output, destination, *, format='cartridge'):
    """Immune organ's same final verification regardless of optical/digital carrier."""
    format_name(format)
    if format=='cartridge':
        from . import cartridge
        return cartridge.unpack(output,destination)
    from . import chromamem
    return chromamem.extract_body(output,destination)
