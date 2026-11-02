"""Read-only deployment probes for independently provisioned BODY/courier users.

No users, services, permissions or credentials are created or changed. The trusted
operator supplies a JSON argv vector selecting the existing courier principal.
An ordinary same-user run must fail qualification. Never run this through MIND tools.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys

def principal():
    if os.name!='nt':return 'uid:'+str(os.getuid())
    raw=subprocess.check_output(['whoami','/user','/fo','csv','/nh'],text=True)
    return 'sid:'+next(csv.reader(io.StringIO(raw)))[1]

def memory_access(pid):
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x0010,False,pid)  # PROCESS_VM_READ
        if handle:kernel.CloseHandle(handle)
        return bool(handle)
    try:
        fd=os.open('/proc/'+str(pid)+'/mem',os.O_RDONLY)
        os.close(fd)
        return True
    except PermissionError:return False
    except OSError:return None  # Unsupported procfs is not proof of denial.

def probe(paths,pid):
    readable=[]
    for path in paths:
        try:
            with open(path,'rb') as stream:stream.read(1)
            readable.append(True)
        except PermissionError:readable.append(False)
        except OSError:readable.append(None)
    return {'principal':principal(),'readable':readable,'body_memory_access':memory_access(pid)}

def qualify(command,paths,pid):
    if (not isinstance(command,list) or not command or
        not all(isinstance(s,str) for s in command) or command.count('{probe}')!=1):
        raise ValueError('Explicit argv vector containing one {probe} argument required')
    if len(paths)<3 or not all(Path(p).is_file() for p in paths):
        raise ValueError('Provide existing private state, key and worker-transcript canary files')
    if type(pid) is not int or pid<=0 or memory_access(pid) is not True:
        raise ValueError('Controller must identify a live Body process it can inspect')
    argv=[str(Path(__file__).resolve()) if s=='{probe}' else s for s in command]
    argv+=['--probe','--body-pid',str(pid)]
    for path in paths:argv+=['--private-path',str(Path(path).resolve())]
    child=subprocess.run(argv,capture_output=True,text=True,timeout=15,check=True)
    receipt=json.loads(child.stdout)
    owner=principal()
    passed=(receipt.get('principal')!=owner and
            isinstance(receipt.get('principal'),str) and
            receipt.get('readable')==[False]*len(paths) and
            receipt.get('body_memory_access') is False)
    return {'result':'PROBES_PASS' if passed else 'UNQUALIFIED','body_principal':owner,
            'courier_probe':receipt,'scope':'OS file and process-handle probes only; provider/tool transcript surfaces require independent checks',
            'acceptance':'OPEN','authority':'NONE'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',action='store_true')
    p.add_argument('--body-pid',type=int)
    p.add_argument('--private-path',action='append',required=True)
    p.add_argument('--courier-command',help='Trusted operator JSON file containing argv with {probe}')
    args=p.parse_args()
    if args.probe:
        result=probe(args.private_path,args.body_pid)
    else:
        if not args.courier_command:p.error('--courier-command is required')
        result=qualify(json.loads(Path(args.courier_command).read_text('utf8')),
                       args.private_path,args.body_pid or os.getpid())
    print(json.dumps(result,indent=2))
    return 0 if args.probe or result['result']=='PROBES_PASS' else 2

if __name__=='__main__':raise SystemExit(main())
