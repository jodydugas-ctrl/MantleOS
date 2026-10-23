"""Optional organ and MIND may be entirely absent; body still functions."""
import sys
sys.path.insert(0, sys.argv[1])
from task_agent import TaskAgent
from kpp_reflex_adapter import run_with_reflex

agent=TaskAgent()
assert run_with_reflex(agent,'add','tea') == {'ok':True,'message':'Added: tea'}
assert run_with_reflex(agent,'list') == {'ok':True,'message':['tea']}
assert run_with_reflex(agent,'bogus') == {'ok':False,'message':'Unknown or invalid command'}
print('PASS standalone body with no organ or MIND')
