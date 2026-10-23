from __future__ import annotations

QUERY_SQL = {
    "surfaces": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE kind IN ('human_surface','surface_reference','surface_factory_output') ORDER BY path,name",
    "surface-without-handler": """
        SELECT n.id,n.name,n.path,n.coverage,n.attributes_json FROM nodes n
        WHERE n.kind IN ('human_surface','surface_reference','surface_factory_output')
        AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.src=n.id AND e.kind IN ('dispatches_to','emits','routes_to','alternate_route_to','resolves_to'))
        ORDER BY n.path,n.name
    """,
    "cli-surfaces": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE json_extract(attributes_json,'$.surface_type') IN ('cli_option','cli_positional') ORDER BY path,name",
    "shortcuts": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE json_extract(attributes_json,'$.surface_type') IN ('keyboard_shortcut','QShortcut') ORDER BY path,name",
    "event-surfaces": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE json_extract(attributes_json,'$.entry_mechanism')='event_override' OR json_extract(attributes_json,'$.surface_type')='os_file_open' ORDER BY path,name",
    "dialog-surfaces": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE json_extract(attributes_json,'$.surface_type')='dialog' ORDER BY path,name",
    "resolution-gaps": "SELECT id,kind,title,status,attributes_json,evidence_ids_json FROM findings WHERE kind='resolution_gap' ORDER BY title,id",
    "subprocess": "SELECT id,name,path,coverage,attributes_json FROM nodes WHERE kind='nest_boundary' AND json_extract(attributes_json,'$.boundary_type')='subprocess' ORDER BY path,id",
    "nest": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE kind IN ('nest_boundary','nest_condition') ORDER BY path,name",
    "extensions": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE kind IN ('extension_receptor_candidate','extension_receptor','capability_factory') ORDER BY path,kind,name",
    "dynamic-registrations": "SELECT id,name,path,coverage,attributes_json FROM nodes WHERE kind IN ('dynamic_registration','surface_factory_output') ORDER BY path,id",
    "recurrence": "SELECT id,name,path,coverage,attributes_json FROM nodes WHERE kind='recurrence_source' ORDER BY path,name",
    "unknown": "SELECT id,kind,name,path,coverage,attributes_json FROM nodes WHERE coverage IN ('UNKNOWN','PARTIAL','BLOCKED') ORDER BY coverage,path,name",
    "acquisition-gaps": "SELECT id,path,size,language,coverage,acquisition_state,provider,provider_object_id FROM files WHERE content_available=0 ORDER BY path",
    "evidence": "SELECT id,file_id,path,start_line,end_line,evidence_class,extractor,excerpt FROM evidence ORDER BY path,start_line,id",
    "semantic-objects": "SELECT id,object_type,subtype,label,coverage,attributes_json FROM semantic_objects ORDER BY object_type,subtype,label,id",
    "semantic-relations": "SELECT id,src,dst,kind,status,attributes_json,evidence_ids_json FROM semantic_relations ORDER BY kind,src,dst,id",
    "completeness": "SELECT id,key,label,state,parent_id,attributes_json,evidence_ids_json FROM completeness_dimensions ORDER BY key",
    "orphan-evidence": """
        SELECT o.id,o.subtype,o.label,o.coverage FROM semantic_objects o
        WHERE o.object_type='EVIDENCE'
        AND NOT EXISTS (SELECT 1 FROM semantic_relations r WHERE r.src=o.id AND r.kind IN ('supports','supports_anchor','derived_from'))
        ORDER BY o.id
    """,
    "reconstruction-anchors": "SELECT id,object_type,subtype,label,coverage,attributes_json FROM semantic_objects WHERE object_type='RECONSTRUCTION_ANCHOR' ORDER BY id",
    "calls": "SELECT id,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind='call_reference' ORDER BY path,json_extract(attributes_json,'$.line'),id",
    "effects": "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind IN ('effect','state_change','feedback','persistence_operation','error_path','control_exit') ORDER BY path,kind,id",
    "state-changes": "SELECT id,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind='state_change' ORDER BY path,id",
    "persistence": "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind IN ('persistence_provider','persistence_operation') ORDER BY path,kind,id",
    "guards": "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind IN ('guard','control_loop','control_exit','error_path','retry_path_candidate') ORDER BY path,kind,id",
    "permissions": "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE (kind='effect' AND name LIKE '%permission%') OR (kind='guard' AND attributes_json LIKE '%permissions_or_availability%') ORDER BY path,kind,id",
    "capabilities": "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes WHERE kind IN ('nest_boundary','effect','extension_receptor','extension_receptor_candidate','capability_factory','persistence_operation') ORDER BY path,kind,name,id",
    "external-writes": """
        SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes
        WHERE kind IN ('effect','persistence_operation') AND (
          json_extract(attributes_json,'$.direction') IN ('write','outbound')
          OR json_extract(attributes_json,'$.effect_type') LIKE '%write%'
          OR json_extract(attributes_json,'$.effect_type') IN ('filesystem_commit','permission_change','print_job','network_request','subprocess_launch','ipc_send','environment_write')
        ) ORDER BY path,kind,name,id
    """,
    "unknown-routes": """
        SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes
        WHERE coverage IN ('UNKNOWN','PARTIAL','BLOCKED')
          AND kind IN ('human_surface','surface_reference','surface_factory_output','event','handler_reference','call_reference','dispatch_case','dynamic_surface_family')
        ORDER BY coverage,path,kind,name,id
    """,
    "disconnected-handlers": """
        SELECT n.id,n.kind,n.name,n.path,n.coverage,n.attributes_json,n.evidence_ids_json FROM nodes n
        WHERE n.kind='handler_reference'
          AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst=n.id AND e.kind IN ('dispatches_to','routes_to','invokes','connects_to','emits','triggers','resolves_to','alternate_route_to'))
        ORDER BY n.path,n.name,n.id
    """,
    "high-connectivity-junctions": """
        WITH degree AS (
          SELECT node_id, COUNT(*) AS degree FROM (
            SELECT src AS node_id FROM edges UNION ALL SELECT dst AS node_id FROM edges
          ) GROUP BY node_id
        )
        SELECT n.id,n.kind,n.name,n.path,n.coverage,d.degree,n.attributes_json
        FROM degree d JOIN nodes n ON n.id=d.node_id
        WHERE d.degree >= 4 ORDER BY d.degree DESC,n.path,n.name,n.id
    """,
    "hidden-surface-candidates": """
        SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes
        WHERE kind IN ('human_surface','surface_reference','surface_factory_output','dynamic_surface_family')
          AND (
            kind IN ('surface_factory_output','dynamic_surface_family')
            OR json_extract(attributes_json,'$.visibility') IN ('hidden','conditional','runtime_populated')
            OR json_extract(attributes_json,'$.surface_type')='keyboard_shortcut'
          )
        ORDER BY path,kind,name,id
    """,
    "nest-dependent-actions": """
        WITH RECURSIVE route(start_id,current_id,depth,visited) AS (
          SELECT id,id,0,'|'||id||'|' FROM nodes
          WHERE kind IN ('human_surface','surface_reference','surface_factory_output')
            AND COALESCE(json_extract(attributes_json,'$.surface_role'),'input')!='presented'
          UNION ALL
          SELECT r.start_id,e.dst,r.depth+1,r.visited||e.dst||'|'
          FROM route r JOIN edges e ON e.src=r.current_id
          WHERE r.depth < 10
            AND e.kind IN ('resolves_to','alternate_route_to','emits','dispatches_to','invokes','triggers','routes_to','calls','crosses_boundary','changes_state','produces_feedback','delivers_async_to','triggers_async')
            AND instr(r.visited,'|'||e.dst||'|')=0
        )
        SELECT DISTINCT s.id,s.kind,s.name,s.path,s.coverage,s.attributes_json
        FROM route r JOIN nodes t ON t.id=r.current_id JOIN nodes s ON s.id=r.start_id
        WHERE t.kind IN ('nest_boundary','effect','persistence_operation','extension_receptor','extension_receptor_candidate','capability_factory')
        ORDER BY s.path,s.name,s.id
    """,
    "capability-without-human-route": """
        WITH RECURSIVE route(current_id,depth,visited) AS (
          SELECT id,0,'|'||id||'|' FROM nodes
          WHERE kind IN ('human_surface','surface_reference','surface_factory_output')
            AND COALESCE(json_extract(attributes_json,'$.surface_role'),'input')!='presented'
          UNION ALL
          SELECT e.dst,r.depth+1,r.visited||e.dst||'|'
          FROM route r JOIN edges e ON e.src=r.current_id
          WHERE r.depth < 10
            AND e.kind IN ('resolves_to','alternate_route_to','emits','dispatches_to','invokes','triggers','routes_to','calls','crosses_boundary','changes_state','produces_feedback','delivers_async_to','triggers_async')
            AND instr(r.visited,'|'||e.dst||'|')=0
        )
        SELECT n.id,n.kind,n.name,n.path,n.coverage,n.attributes_json,n.evidence_ids_json
        FROM nodes n
        WHERE n.kind IN ('nest_boundary','effect','persistence_operation','extension_receptor','extension_receptor_candidate','capability_factory','framework_capability')
          AND NOT EXISTS (SELECT 1 FROM route r WHERE r.current_id=n.id)
        ORDER BY n.path,n.kind,n.name,n.id
    """,
    "authentication-permissions": """
        SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes
        WHERE (kind='effect' AND (LOWER(name) LIKE '%permission%' OR LOWER(name) LIKE '%auth%' OR LOWER(name) LIKE '%credential%' OR LOWER(name) LIKE '%token%'))
           OR (kind='guard' AND (LOWER(attributes_json) LIKE '%permission%' OR LOWER(attributes_json) LIKE '%auth%' OR LOWER(attributes_json) LIKE '%credential%' OR LOWER(attributes_json) LIKE '%token%'))
           OR (kind='nest_boundary' AND (LOWER(attributes_json) LIKE '%permission%' OR LOWER(attributes_json) LIKE '%auth%'))
        ORDER BY path,kind,name,id
    """,
}

RELEASE_ACCEPTANCE_QUERIES = [
    "surface-without-handler", "subprocess", "extensions", "external-writes", "unknown-routes",
    "nest-dependent-actions", "disconnected-handlers", "high-connectivity-junctions",
    "dynamic-registrations", "hidden-surface-candidates", "capability-without-human-route",
    "authentication-permissions",
]
