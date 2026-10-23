"""Bounded PE/CLI metadata declarations, using bytes only; never load a binary.

Layouts follow Microsoft PE/COFF and ECMA-335 Partition II. This is not an IL
reader, decompiler, signature interpreter, executable validator or authenticator.
"""
import time
from .common import ScanError, digest, sha

# Standard column layouts: fixed byte sizes, string/blob/GUID heap indices,
# simple table indices (integers prefixed by t), or named coded indices.
CODES = {
    "TypeDefOrRef": (2,(2,1,27)), "HasConstant": (2,(4,8,23)),
    "HasCustomAttribute": (5,(6,4,1,2,8,9,10,0,14,23,20,17,26,27,32,35,38,39,40,42,44,43)),
    "HasFieldMarshal": (1,(4,8)), "HasDeclSecurity": (2,(2,6,32)),
    "MemberRefParent": (3,(2,1,26,6,27)), "HasSemantics": (1,(20,23)),
    "MethodDefOrRef": (1,(6,10)), "MemberForwarded": (1,(4,6)),
    "Implementation": (2,(38,35,39)), "CustomAttributeType": (3,(None,None,6,10)),
    "ResolutionScope": (2,(0,26,35,1)), "TypeOrMethodDef": (1,(2,6)),
}
TABLES = {
    0:(2,'s','g','g','g'), 1:('ResolutionScope','s','s'),
    2:(4,'s','s','TypeDefOrRef','t4','t6'), 3:('t4',), 4:(2,'s','b'),
    5:('t6',), 6:(4,2,2,'s','b','t8'), 7:('t8',), 8:(2,2,'s'),
    9:('t2','TypeDefOrRef'), 10:('MemberRefParent','s','b'),
    11:(2,'HasConstant','b'), 12:('HasCustomAttribute','CustomAttributeType','b'),
    13:('HasFieldMarshal','b'), 14:(2,'HasDeclSecurity','b'), 15:(2,4,'t2'),
    16:(4,'t4'), 17:('b',), 18:('t2','t20'), 19:('t20',),
    20:(2,'s','TypeDefOrRef'), 21:('t2','t23'), 22:('t23',), 23:(2,'s','b'),
    24:(2,'t6','HasSemantics'), 25:('t2','MethodDefOrRef','MethodDefOrRef'),
    26:('s',), 27:('b',), 28:(2,'MemberForwarded','s','t26'), 29:(4,'t4'),
    30:(4,4), 31:(4,), 32:(4,2,2,2,2,4,'b','s','s'), 33:(4,), 34:(4,4,4),
    35:(2,2,2,2,4,'b','s','s','b'), 36:(4,'t35'), 37:(4,4,4,'t35'),
    38:(4,'s','b'), 39:(4,4,'s','s','Implementation'), 40:(4,4,'s','Implementation'),
    41:('t2','t2'), 42:(2,2,'TypeOrMethodDef','s'), 43:('MethodDefOrRef','b'),
    44:('t42','TypeDefOrRef'),
}
GAPS = [
    "Bounded Windows PE/CLI declaration metadata only; not a complete executable or metadata validator.",
    "No binary loading, IL/method-body interpretation, decompilation, signature decoding, dependency resolution or runtime behavior.",
    "Import/PInvoke entries declare boundaries; they do not prove a library is present, invoked or safe.",
    "Nested type ownership, properties/events, attributes, generics and advanced metadata/signatures are not interpreted.",
]


class UnsupportedMetadata(ScanError):
    pass


class PE:
    def __init__(self, data, deadline=None):
        self.data = data
        self.deadline = min(time.monotonic() + 5,deadline) if deadline is not None else time.monotonic() + 5
        if len(data) > 2000000: raise ScanError("Native PE source byte budget exceeded")
        if data[:2] != b'MZ': raise UnsupportedMetadata("Not a supported Windows PE image; bytes inventoried only")
        offset = self.u(0x3c,4)
        if offset < 64 or self.read(offset,4) != b'PE\0\0': raise ScanError("Invalid PE header signature or offset")
        coff = offset + 4; self.machine = self.u(coff,2); sections = self.u(coff + 2,2)
        if not 1 <= sections <= 96: raise ScanError("Native PE section budget or invalid section count")
        optional_size = self.u(coff + 16,2); optional = coff + 20
        self.read(optional,optional_size); magic = self.u(optional,2)
        if magic not in (0x10b,0x20b): raise UnsupportedMetadata("Unsupported PE optional header format")
        self.width = 8 if magic == 0x20b else 4
        directory_start, count_offset = ((112,108) if self.width == 8 else (96,92))
        if optional_size < directory_start: raise ScanError("Truncated PE optional header")
        directory_count = self.u(optional + count_offset,4)
        if directory_count > 16 or optional_size < directory_start + directory_count * 8:
            raise ScanError("Invalid PE directory count or size")
        self.headers_size = self.u(optional + 60,4)
        if not optional + optional_size + sections * 40 <= self.headers_size <= len(data):
            raise ScanError("PE header range is invalid")
        self.directories = [tuple(self.u(optional + directory_start + i * 8 + j,4) for j in (0,4)) for i in range(directory_count)]
        self.sections = []
        for i in range(sections):
            position = optional + optional_size + i * 40
            header = self.read(position,40)
            virtual_size, rva, raw_size, raw = [self.u(position + j,4) for j in (8,12,16,20)]
            if rva < self.headers_size or rva + max(virtual_size,raw_size) > 0x100000000:
                raise ScanError('Invalid PE virtual section range')
            if raw_size:
                if raw < self.headers_size: raise ScanError("PE section overlaps headers")
                self.read(raw,raw_size)
            item = {'name':header[:8].split(b'\0',1)[0].decode('ascii',errors='replace'),
                    'rva':rva,'virtual_size':virtual_size,'raw_size':raw_size,'raw_offset':raw,'header_offset':position}
            for earlier in self.sections:
                if raw_size and earlier['raw_size'] and max(raw,earlier['raw_offset']) < min(raw + raw_size,earlier['raw_offset'] + earlier['raw_size']):
                    raise ScanError("Overlapping PE raw sections")
                if max(rva,earlier['rva']) < min(rva + max(virtual_size,raw_size),earlier['rva'] + max(earlier['virtual_size'],earlier['raw_size'])):
                    raise ScanError("Overlapping PE virtual sections")
            self.sections.append(item)

    def read(self, offset, count):
        if time.monotonic() > self.deadline: raise ScanError("Native PE deadline exceeded")
        if type(offset) is not int or type(count) is not int or offset < 0 or count < 0 or offset + count > len(self.data):
            raise ScanError("Native PE byte range out of bounds")
        return self.data[offset:offset + count]

    def u(self, offset, size):
        return int.from_bytes(self.read(offset,size),'little')

    def rva(self, address, count=1):
        if address < self.headers_size and address + count <= self.headers_size:
            self.read(address,count); return address
        matches = [section['raw_offset'] + address - section['rva'] for section in self.sections if
                   section['rva'] <= address and address + count <= section['rva'] + section['raw_size']]
        if len(matches) != 1: raise ScanError("PE RVA is absent, ambiguous or outside stored section bytes")
        self.read(matches[0],count); return matches[0]

    def directory(self, index):
        return self.directories[index] if index < len(self.directories) else (0,0)

    def cstring(self, address):
        offset = self.rva(address)
        # Every byte must map in the same stored section, not adjacent raw data.
        end = self.data.find(b'\0',offset,min(len(self.data),offset + 1025))
        if end < 0: raise ScanError("PE string terminator/string budget exceeded")
        self.rva(address,end - offset + 1)
        return self.read(offset,end - offset).decode('utf-8')

    def imports(self):
        address, size = self.directory(1)
        if not address and not size: return []
        if not address or size < 20 or size > 256 * 20: raise ScanError("PE import directory budget/size invalid")
        result = []; start = self.rva(address,size)
        for i in range(size // 20):
            position = start + i * 20
            values = [self.u(position + j,4) for j in (0,4,8,12,16)]
            if not any(values): return result
            name = self.cstring(values[3]); thunk = values[0] or values[4]
            if not name or not thunk: raise ScanError("Invalid PE import descriptor")
            for j in range(2049):
                value = self.u(self.rva(thunk + j * self.width,self.width),self.width)
                if value == 0: break
                if len(result) >= 2048: raise ScanError("PE import record budget exceeded")
                ordinal = bool(value & (1 << (self.width * 8 - 1)))
                member = '#' + str(value & 0xffff) if ordinal else self.cstring(value + 2)
                result.append((name,member,position,ordinal))
            else: raise ScanError("PE import thunk termination budget exceeded")
        raise ScanError("Unterminated PE import directory")


class Metadata:
    def __init__(self, image):
        self.image = image
        address, size = image.directory(14)
        if not address and not size: raise UnsupportedMetadata("No managed CLI directory; native PE headers/import declarations only")
        if not address or size < 72: raise ScanError("Invalid CLI header size")
        cli = image.rva(address,72)
        if image.u(cli,4) < 72: raise ScanError("Invalid CLI header length")
        self.flags = image.u(cli + 16,4)
        metadata_address, self.size = image.u(cli + 8,4), image.u(cli + 12,4)
        if not 20 <= self.size <= 2000000: raise ScanError("CLI metadata size budget exceeded")
        self.start = image.rva(metadata_address,self.size)
        if image.read(self.start,4) != b'BSJB': raise ScanError("Invalid CLI metadata signature")
        length = self.u(12,4)
        if not 1 <= length <= 256: raise ScanError("CLI metadata version byte budget exceeded")
        self.version = self.read(16,length).rstrip(b'\0').decode('utf-8')
        position = (16 + length + 3) & ~3
        streams = self.u(position + 2,2); position += 4
        if not 1 <= streams <= 16: raise ScanError("CLI stream count budget exceeded")
        self.streams = {}
        for _ in range(streams):
            offset, count = self.u(position,4), self.u(position + 4,4)
            end = position + 8
            while end < position + 40 and self.read(end,1) != b'\0': end += 1
            if end >= position + 40: raise ScanError("CLI stream name budget exceeded")
            name = self.read(position + 8,end - position - 8).decode('ascii')
            if name in self.streams: raise ScanError("Duplicate CLI metadata stream")
            self.read(offset,count); self.streams[name] = (offset,count)
            position = (end + 4) & ~3
        for name,(offset,count) in self.streams.items():
            if count and offset < position: raise ScanError("CLI stream overlaps metadata headers")
            for other,(other_offset,other_count) in self.streams.items():
                if name != other and count and other_count and max(offset,other_offset) < min(offset + count,other_offset + other_count):
                    raise ScanError("Overlapping CLI streams")
        table_names = [name for name in ('#~','#-') if name in self.streams]
        if len(table_names) != 1 or '#Strings' not in self.streams: raise UnsupportedMetadata("Unsupported CLI table/string stream layout")
        table_start, table_size = self.streams[table_names[0]]
        if table_size < 24: raise ScanError("Truncated CLI table header")
        heap_flags = self.u(table_start + 6,1)
        if heap_flags & ~7: raise UnsupportedMetadata("Unsupported CLI heap flags")
        self.heap_widths = {name:4 if heap_flags & flag else 2 for name,flag in (('s',1),('g',2),('b',4))}
        valid = self.u(table_start + 8,8); position = table_start + 24
        self.counts = {}; total = 0
        for number in range(64):
            if valid & (1 << number):
                count = self.u(position,4); position += 4
                if number not in TABLES: raise UnsupportedMetadata("Unsupported CLI metadata table " + str(number))
                total += count
                if count > 100000 or total > 200000: raise ScanError("CLI row budget exceeded")
                self.counts[number] = count
        self.positions = {}; self.widths = {}
        for number,count in self.counts.items():
            widths = tuple(self.width(column) for column in TABLES[number]); row_size = sum(widths)
            if position + count * row_size > table_start + table_size: raise ScanError("Truncated CLI table rows")
            self.positions[number] = position; self.widths[number] = widths
            position += count * row_size

    def read(self, offset, count):
        if offset < 0 or count < 0 or offset + count > self.size: raise ScanError("CLI metadata range out of bounds")
        return self.image.read(self.start + offset,count)

    def u(self, offset, count):
        return int.from_bytes(self.read(offset,count),'little')

    def width(self, column):
        if type(column) is int: return column
        if column in self.heap_widths: return self.heap_widths[column]
        if column.startswith('t'): return 4 if self.counts.get(int(column[1:]),0) >= 65536 else 2
        bits, tables = CODES[column]
        return 4 if any(self.counts.get(number,0) >= (1 << (16 - bits)) for number in tables if number is not None) else 2

    def rows(self, number):
        widths = self.widths.get(number,())
        for row in range(self.counts.get(number,0)):
            position = self.positions[number] + row * sum(widths); values = []
            for width in widths:
                values.append(self.u(position,width)); position += width
            yield row + 1, values, self.start + position - sum(widths)

    def string(self, index):
        offset, count = self.streams['#Strings']
        if index == 0: return ''
        if not 0 < index < count: raise ScanError("Invalid CLI string heap index")
        end = self.image.data.find(b'\0',self.start + offset + index,self.start + offset + min(count,index + 1025))
        if end < 0: raise ScanError("CLI string budget/terminator exceeded")
        return self.image.read(self.start + offset + index,end - self.start - offset - index).decode('utf-8')

    def blob_hash(self, index):
        if index == 0: return sha(b'')
        if '#Blob' not in self.streams: raise ScanError("Referenced CLI blob heap missing")
        offset, count = self.streams['#Blob']
        if not 0 < index < count: raise ScanError("Invalid CLI blob heap index")
        first = self.u(offset + index,1)
        width = 1 if first < 0x80 else 2 if first < 0xc0 else 4 if first < 0xe0 else 0
        if not width or index + width > count: raise ScanError("Invalid CLI compressed blob length")
        raw = self.read(offset + index,width)
        length = first if width == 1 else ((first & (0x3f if width == 2 else 0x1f)) << (8 * (width - 1))) | int.from_bytes(raw[1:],'big')
        if length > 65536 or index + width + length > count: raise ScanError("CLI signature blob range/budget exceeded")
        return sha(self.read(offset + index + width,length))


def extract_pe(path, data, *, deadline=None):
    from .adapters import Builder
    builder = Builder(path,sha(data),module_line=None,module_end_line=None)
    def add(kind,name,owner,position,**attributes):
        if position < 0 or position >= len(data): raise ScanError("Native binary declaration offset invalid")
        return builder.add(kind,name,None,None,owner,0,analysis_origin='native',
                           byte_offset=position,declaration_only=True,syntax_sha256=digest([kind,name,attributes]),**attributes)
    try: image = PE(data,deadline)
    except UnsupportedMetadata as error:
        result = builder.result('pe',[str(error),*GAPS]); result['coverage'] = 'BOUNDED_BINARY_METADATA'; return result
    builder.nodes[0]['attributes'].update(analysis_origin='native',container='PE',machine=image.machine,pointer_bytes=image.width,declaration_only=True)
    for section in image.sections: add('binary_section',section['name'],builder.module,section['header_offset'],**{key:value for key,value in section.items() if key not in ('name','header_offset')})
    for library,member,position,ordinal in image.imports():
        add('native_boundary',member,builder.module,position,library=library,ordinal_import=ordinal,boundary='PE_IMPORT')
    try: metadata = Metadata(image)
    except UnsupportedMetadata as error:
        result = builder.result('pe',[str(error),*GAPS]); result['coverage'] = 'BOUNDED_BINARY_METADATA'; return result
    builder.nodes[0]['attributes'].update(cli_metadata_version=metadata.version,cli_flags=metadata.flags)
    for _,values,position in metadata.rows(0): add('managed_module',metadata.string(values[1]),builder.module,position)
    for _,values,position in metadata.rows(32):
        add('assembly',metadata.string(values[7]),builder.module,position,version='.'.join(map(str,values[1:5])),culture=metadata.string(values[8]),public_key_sha256=metadata.blob_hash(values[6]))
    for _,values,position in metadata.rows(35):
        add('import',metadata.string(values[6]),builder.module,position,module='',dependency_kind='ASSEMBLY_REFERENCE',version='.'.join(map(str,values[:4])))
    gaps = list(GAPS)
    if metadata.counts.get(3) or metadata.counts.get(5):
        gaps.append('Unoptimized CLI field/method pointer indirection not interpreted; member/ownership coverage omitted')
    else:
        types = list(metadata.rows(2)); type_nodes = {}; members = {}
        for row,values,position in types:
            name = '.'.join(part for part in (metadata.string(values[2]),metadata.string(values[1])) if part)
            if not name: raise ScanError("Empty CLI type declaration name")
            type_nodes[row] = add('class',name,builder.module,position,flags=values[0],metadata_token=hex(0x02000000 | row))
        for column,table,kind,name_column,signature_column in ((4,4,'field',1,2),(5,6,'function',3,4)):
            rows = list(metadata.rows(table)); count = len(rows)
            starts = [values[column] for _,values,_ in types] + [count + 1]
            if any(not 1 <= value <= count + 1 for value in starts) or starts != sorted(starts): raise ScanError("Invalid CLI member ownership list")
            for i,(type_row,_,_) in enumerate(types):
                for row,values,position in rows[starts[i] - 1:starts[i + 1] - 1]:
                    name = metadata.string(values[name_column])
                    if not name: raise ScanError("Empty CLI member declaration name")
                    members[(table,row)] = add(kind,name,type_nodes[type_row],position,metadata_token=hex((table << 24) | row),
                        signature_blob_sha256=metadata.blob_hash(values[signature_column]),method_body='NOT_READ')
        modules = {row:metadata.string(values[0]) for row,values,_ in metadata.rows(26)}
        for _,values,position in metadata.rows(28):
            flags,coded,name,module = values; table = 6 if coded & 1 else 4; row = coded >> 1
            if (table,row) not in members or module not in modules: raise ScanError("Invalid CLI native-boundary reference")
            add('native_boundary',metadata.string(name),members[(table,row)],position,library=modules[module],mapping_flags=flags,boundary='CLI_IMPLMAP')
    result = builder.result('pe',gaps); result['coverage'] = 'BOUNDED_BINARY_METADATA'
    return result
