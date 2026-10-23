"""After-success is optional; errors/failed commands do not create events."""
import sys
sys.path.insert(0, sys.argv[1])
from task_agent import TaskAgent
from continuity import Continuity
from kpp_reflex_adapter import run_with_reflex

organ, agent = Continuity(), TaskAgent()
assert run_with_reflex(agent,'add','tea',organ=organ)=={'ok':True,'message':'Added: tea'}
assert run_with_reflex(agent,'unknown',organ=organ)=={'ok':False,'message':'Unknown or invalid command'}
assert run_with_reflex(agent,'list',organ=organ)=={'ok':True,'message':['tea']}
assert [r['command'] for r in organ.recall()] == ['add','list']
assert [r['response'] for r in organ.recall()] == [
    {'ok':True,'message':'Added: tea'}, {'ok':True,'message':['tea']}]
class FailingOrgan:
    def on_success(self,*args,**kwargs):raise RuntimeError('organ broken')
assert run_with_reflex(TaskAgent(),'add','tea',organ=FailingOrgan())=={'ok':True,'message':'Added: tea'}
class Mutator:
    def on_success(self,response,*args,**kwargs):response['message']='tampered'
assert run_with_reflex(TaskAgent(),'add','tea',organ=Mutator())=={'ok':True,'message':'Added: tea'}
print('PASS success-only events and observer failure isolation')
