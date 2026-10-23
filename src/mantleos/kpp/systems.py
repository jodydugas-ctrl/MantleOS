"""One system, exposed through MantleOS and standalone KPP distributions."""
from .. import anchors, cells, tissue, kitchen, anchor_language


def describe():
    from .. import __version__
    return {'schema': 'mantle.systems/1', 'mantleos': __version__,
            'implementation': 'mantleos.kpp',
            'anchor_types': list(anchors.TYPES), 'anchor_application': anchors.SCHEMA,
            'anchor_definitions': {name: {'type': item.type, 'singularity': item.singularity}
                                   for name, item in anchors.DEFINITIONS.items()},
            'recipe_binding': 'mantle.kpp-binding/1',
            'cell_schema': cells.SCHEMA, 'cell_kernels': cells.KERNELS,
            'program_schema': tissue.PROGRAM_SCHEMA, 'tissue_schema': tissue.TISSUE_SCHEMA,
            'deterministic_profiles': sorted(tissue.PROFILES),
            'hosted_profile': 'AGENTIC/0.2; explicit host inputs and authority required',
            'scan_schema': 'scan.report/1', 'discovery_schema': 'mantle.parallel-discovery/1',
            'body_api': 'mantleos.organism / mantleos.lifecycle',
            'memory_api': 'mantleos.engram / mantleos.continuity',
            'carrier_api': 'mantleos.cartridge / mantleos.chromamem',
            'app_construction': 'mantleos.kpp.build; preview first, then bounded Chase over the same recipe',
            'approval': 'Evidence and Anchor applications never grant Baker or host approval',
            'runtime_dependencies': []}
