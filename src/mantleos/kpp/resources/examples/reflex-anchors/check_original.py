"""Pinned fixed-oracle original commands; no baseline comparison alone."""
import sys
sys.path.insert(0, sys.argv[1])
from task_agent import TaskAgent, run_command
from kpp_reflex_adapter import run_with_reflex

before, after = TaskAgent(), TaskAgent()
cases = [('add','tea',{'ok':True,'message':'Added: tea'}),
         ('unknown',None,{'ok':False,'message':'Unknown or invalid command'}),
         ('list',None,{'ok':True,'message':['tea']})]
for name, value, expected in cases:
    assert run_command(before,name,value) == expected
    assert run_with_reflex(after,name,value) == expected
assert before.tasks == after.tasks == ['tea']
print('PASS pinned original outputs and state')
