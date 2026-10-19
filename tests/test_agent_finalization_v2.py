import json
from dataclasses import replace
from types import SimpleNamespace
from app.database import Store
from app.config import config,runtime_scope


def test_agent_reserves_final_round_for_answer_instead_of_searching_forever(tmp_path,monkeypatch):
    import app.agent as agent
    tools_seen=[]
    def complete(store,messages,tools=None,**kwargs):
        tools_seen.append(tools)
        if tools is None:
            message=SimpleNamespace(tool_calls=[],content=json.dumps({'summary':'No approved market conclusion','claims':[],'limitations':[]}))
            dumped={'role':'assistant','content':message.content}
        else:
            call=SimpleNamespace(id='c'+str(len(tools_seen)),function=SimpleNamespace(name='research',arguments='{"query":"City evidence"}'))
            message=SimpleNamespace(tool_calls=[call],content=None)
            dumped={'role':'assistant','content':None,'tool_calls':[{'id':call.id,'type':'function','function':{'name':'research','arguments':'{"query":"City evidence"}'}}]}
        message.model_dump=lambda **kwargs:dumped
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
    monkeypatch.setattr(agent,'completion',complete)
    with runtime_scope(replace(config(),max_rounds=3)):
        result=agent.ask(Store(tmp_path/'db.sqlite3'),'Assess missing City evidence')
    assert result['status']=='SUCCESS' and result['claims']==[]
    assert len(tools_seen)==3 and tools_seen[-1] is None
