ADMIN={"Authorization":"Basic cm9vdDpyb290"}  # root:root
def employee_payload(email='test@demo.example.com'):
 return {"full_name":"Test User","email":email,"department":"Finance","role":"Analyst","preferred_language":"az","privilege_level":3,"access_sensitivity":4,"social_exposure":4}
def test_health(client): assert client.get('/api/v1/health').status_code==200
def test_end_to_end_and_password_never_persisted(client):
    e=client.post('/api/v1/employees',json=employee_payload()).json(); assert e['department']=='Finance'
    risk=client.get(f"/api/v1/employees/{e['id']}/risk").json(); assert 0<=risk['score']<=100 and risk['factors']
    ctx=client.get(f"/api/v1/employees/{e['id']}/context").json(); assert len(ctx)>=3
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"link inspection","difficulty":"medium"}).json(); assert s['status']=='REVIEW_REQUIRED'
    s=client.post(f"/api/v1/scenarios/{s['id']}/approve").json(); assert s['status']=='APPROVED'
    c=client.post('/api/v1/campaigns',json={"scenario_id":s['id'],"name":"Test Campaign"}).json()
    launch=client.post(f"/api/v1/campaigns/{c['id']}/launch",headers=ADMIN).json(); session=launch['session_id']
    secret='RealPasswordThatMustNeverPersist!123'
    ev=client.post(f'/api/v1/simulation/{session}/event',json={"session_id":session,"event_type":"credential_simulation_submitted","password":secret}).json()
    assert ev['safe_metadata']=={"credential_submitted":True,"credential_stored":False}; assert secret not in str(ev)
    audit=client.get('/api/v1/audit').text; assert secret not in audit
    a=client.get(f"/api/v1/campaigns/{c['id']}/analytics").json(); assert a['submission_rate']==100.0

def test_employee_crud_and_invalid(client):
    e=client.post('/api/v1/employees',json=employee_payload('x@demo.example.com')); assert e.status_code==201
    assert client.post('/api/v1/employees',json=employee_payload('x@demo.example.com')).status_code==409
    eid=e.json()['id']; assert client.patch(f'/api/v1/employees/{eid}',json={"role":"Senior Analyst"}).json()['role']=='Senior Analyst'
    assert client.delete(f'/api/v1/employees/{eid}').status_code==204
    assert client.get(f'/api/v1/employees/{eid}').status_code==404

def test_delete_employee_cascades_dependents(client):
    e=client.post('/api/v1/employees',json=employee_payload('cascade@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"easy"}).json()
    assert s['status']=='REVIEW_REQUIRED'
    assert client.delete(f"/api/v1/employees/{e['id']}").status_code==204
    # dependent scenario must be gone, not orphaned
    assert client.get(f"/api/v1/scenarios").json()==[]

def test_edit_and_one_click_launch(client):
    e=client.post('/api/v1/employees',json=employee_payload('flow@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"awareness","difficulty":"medium"}).json()
    # edit before approval
    r=client.patch(f"/api/v1/scenarios/{s['id']}",json={"subject":"[SIMULATION] Edited subject"})
    assert r.status_code==200 and r.json()['subject']=="[SIMULATION] Edited subject"
    # unsafe edit (landing loses required safety wording) is rejected
    assert client.patch(f"/api/v1/scenarios/{s['id']}",json={"landing_page_message":"Please log in now."}).status_code==422
    # launch before approval is blocked
    assert client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).status_code==409
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    # editing an approved scenario is blocked
    assert client.patch(f"/api/v1/scenarios/{s['id']}",json={"subject":"x"}).status_code==409
    # one-click launch
    launch=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN)
    assert launch.status_code==200
    body=launch.json()
    assert body['session_id'] and body['simulation_url'].endswith('/simulate/'+body['session_id'])

def test_simulation_returns_full_message(client):
    e=client.post('/api/v1/employees',json=employee_payload('sim@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"awareness","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    launch=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()
    sim=client.get(f"/api/v1/simulation/{launch['session_id']}").json()
    for k in ("sender","recipient","subject","email_body","pretext","landing_page_message"):
        assert sim.get(k), f"simulation missing {k}"
    assert e['email'] in sim['recipient']
    assert sim['email_body'].count('. ') >= 2  # a multi-sentence lure, not a stub

def test_hr_source_and_idempotent_sync(client):
    src=client.get('/api/v1/hr/source').json()
    assert len(src) > 5 and src[0]['external_id']
    first=client.post('/api/v1/hr/sync').json()
    assert first['created'] == len(src) and first['updated'] == 0
    # second sync updates in place, never duplicates
    again=client.post('/api/v1/hr/sync').json()
    assert again['created'] == 0 and again['updated'] == len(src)
    emps=client.get('/api/v1/employees').json()
    assert len(emps) == len(src)
    assert all(e['source'] == 'mock-hr' and e['external_id'] for e in emps)

def _factor(risk, key):
    return next(f['points'] for f in risk['factors'] if f['key'] == key)

def test_risk_is_role_dept_language_aware(client):
    client.post('/api/v1/hr/sync')
    emps={e['role']: e['id'] for e in client.get('/api/v1/employees').json()}
    cfo=client.get(f"/api/v1/employees/{emps['Chief Financial Officer']}/risk").json()
    spec=client.get(f"/api/v1/employees/{emps['Marketing Specialist']}/risk").json()
    assert _factor(cfo,'role_privilege') > _factor(spec,'role_privilege')
    assert cfo['score'] > spec['score']
    # language is an explicit dimension of the profile schema
    assert {'role_privilege','department_exposure','data_sensitivity','social_exposure','language_exposure'} <= {f['key'] for f in cfo['factors']}

def test_profile_endpoint_bundles_persona_risk_context(client):
    client.post('/api/v1/hr/sync')
    eid=client.get('/api/v1/employees').json()[0]['id']
    p=client.get(f"/api/v1/employees/{eid}/profile").json()
    assert p['employee']['id']==eid and 0<=p['risk']['score']<=100 and len(p['context'])>=3

def test_generation_multilingual_and_difficulty(client):
    client.post('/api/v1/hr/sync')
    emps=client.get('/api/v1/employees').json()
    az=[e for e in emps if e['preferred_language']=='az'][0]
    en=[e for e in emps if e['preferred_language']=='en'][0]
    gen=lambda eid,d: client.post('/api/v1/scenarios/generate',json={"employee_id":eid,"objective":"x","difficulty":d}).json()
    saz, sen = gen(az['id'],"medium"), gen(en['id'],"medium")
    assert 'password' in saz['landing_page_message'].lower() and 'password' in sen['landing_page_message'].lower()
    assert 'Salam' in saz['email_body']            # Azerbaijani output
    assert saz['email_body'] != sen['email_body']  # language actually differs
    easy, hard = gen(en['id'],"easy"), gen(en['id'],"hard")
    assert easy['subject'] != hard['subject'] and easy['email_body'] != hard['email_body']

def test_operational_context_is_rich_and_varied(client):
    client.post('/api/v1/hr/sync')
    emps=client.get('/api/v1/employees').json()
    a=client.get(f"/api/v1/employees/{emps[0]['id']}/context").json()
    b=client.get(f"/api/v1/employees/{emps[1]['id']}/context").json()
    kinds={i['kind'] for i in a}
    assert {'ticket','calendar','communication'} <= kinds          # three synthetic sources
    tickets=[i for i in a if i['kind']=='ticket']
    assert all(i['metadata_json'].get('ticket_id') and i['metadata_json'].get('priority') for i in tickets)
    # communication metadata never carries message content
    comms=[i for i in a if i['kind']=='communication'][0]
    assert comms['metadata_json'].get('content_excluded') is True
    # different personas get different tickets
    ids_a={i['metadata_json']['ticket_id'] for i in a if i['kind']=='ticket'}
    ids_b={i['metadata_json']['ticket_id'] for i in b if i['kind']=='ticket'}
    assert ids_a != ids_b

def test_scenario_has_quality_assessment(client):
    e=client.post('/api/v1/employees',json=employee_payload('q@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    assert isinstance(s['quality_score'],(int,float)) and 0<=s['quality_score']<=100
    assert isinstance(s['quality_notes'],list)

def test_no_credential_persisted_anywhere(client):
    from app.db import engine, Base
    e=client.post('/api/v1/employees',json=employee_payload('vault@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    launch=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()
    secret="SuperSecret_NeverStore_991155"
    ev=client.post(f"/api/v1/simulation/{launch['session_id']}/event",json={"session_id":launch['session_id'],"event_type":"credential_simulation_submitted","password":secret})
    assert ev.status_code==201
    # the submitted value must not appear in ANY row of ANY table
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            blob=" ".join(str(v) for row in conn.execute(table.select()).fetchall() for v in row)
            assert secret not in blob, f"secret leaked into {table.name}"

def test_prompt_layer_builds_system_and_user():
    from app.llm import prompts
    payload={"employee":{"full_name":"Test User","department":"Finance","role":"Analyst","preferred_language":"az"},
             "context":[{"title":"Finance access review"}],"objective":"x","difficulty":"hard"}
    assert prompts.render_scenario(payload)['difficulty']=='hard'
    system,user=prompts.build_prompt(payload)
    assert 'Azerbaijani' in system and user['language']=='az'

def test_russian_generation(client):
    e=client.post('/api/v1/employees',json={**employee_payload('ru@demo.example.com'),"preferred_language":"ru"}).json()
    # explicit language override also works
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium","language":"ru"}).json()
    assert 'Здравствуйте' in s['email_body']                       # Cyrillic Russian output
    # the chosen context anchor is woven into the body, localized (not English)
    ctx=client.get(f"/api/v1/employees/{e['id']}/context").json()
    anchor=max(ctx,key=lambda c:c['metadata_json'].get('anchor',0))
    assert anchor['title'] in s['email_body']
    assert 'password' in s['landing_page_message'].lower()          # safety words retained
    assert 'simulation' in s['landing_page_message'].lower()
    from app.llm import prompts
    assert prompts.normalize_language('ru') == 'ru' and 'Russian' in prompts.LANGUAGES.values()

def test_launch_requires_admin_credentials(client):
    import base64
    e=client.post('/api/v1/employees',json=employee_payload('auth@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    assert client.post(f"/api/v1/scenarios/{s['id']}/launch").status_code==401          # no creds
    bad={"Authorization":"Basic "+base64.b64encode(b'root:wrong').decode()}
    assert client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=bad).status_code==401  # wrong creds
    assert client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).status_code==200  # correct

def test_regenerate_updates_in_place(client):
    e=client.post('/api/v1/employees',json=employee_payload('regen@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    before=client.get('/api/v1/scenarios').json()
    r=client.post(f"/api/v1/scenarios/{s['id']}/regenerate")
    assert r.status_code==200 and r.json()['id']==s['id']       # same scenario id, not a new one
    assert len(client.get('/api/v1/scenarios').json())==len(before)  # no extra scenario created
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    assert client.post(f"/api/v1/scenarios/{s['id']}/regenerate").status_code==409  # not editable once approved

def test_campaign_requires_approval(client):
    e=client.post('/api/v1/employees',json=employee_payload()).json(); s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"awareness","difficulty":"easy"}).json()
    assert client.post('/api/v1/campaigns',json={"scenario_id":s['id'],"name":"Blocked campaign"}).status_code==409

def test_launch_tolerates_any_body_shape(client):
    # A client (e.g. a stale cached bundle) may POST a non-object body to launch.
    # It must never 422 on body shape; name is only read when the body is an object.
    e=client.post('/api/v1/employees',json=employee_payload('body@demo.example.com')).json()
    for raw in ['"a string"','[1,2]','123','null','{}']:
        s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
        client.post(f"/api/v1/scenarios/{s['id']}/approve")
        r=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers={**ADMIN,"Content-Type":"application/json"},content=raw)
        assert r.status_code==200, f"body {raw!r} -> {r.status_code} {r.text}"

def test_llm_response_is_coerced_to_valid_scenario():
    # A real LLM can return partial / wrong-typed / non-JSON content. Coercion
    # must always yield a schema-valid scenario (filling gaps from the template)
    # so a flaky model never surfaces as a 500/503 to the user.
    from app.llm import providers
    payload={"employee":{"full_name":"Test User","department":"Finance","role":"Analyst","preferred_language":"az"},
             "context":[{"title":"Finance access review","anchor":9}],"objective":"x","difficulty":"medium"}
    required=providers.prompts.SCENARIO_SCHEMA["required"]
    for raw in [
        {},                                                   # model returned nothing usable
        {"subject":"Only a subject"},                         # missing most keys
        {"risk_indicators":"not-a-list","pretext":123},       # wrong types
        {"scenario":{"subject":"Wrapped","email_body":"b"}},  # single-key envelope
        "this is not an object",                              # not even a dict
    ]:
        out=providers._coerce_scenario(raw if isinstance(raw,dict) else {},payload)
        assert all(k in out for k in required)                # every required key present
        assert all(isinstance(out[k],str) and out[k] for k in required if k!="risk_indicators")
        assert isinstance(out["risk_indicators"],list) and all(isinstance(x,str) for x in out["risk_indicators"])
    # a good value from the model is preserved, not overwritten by the template
    kept=providers._coerce_scenario({"subject":"Kept subject","risk_indicators":["a","b","c"]},payload)
    assert kept["subject"]=="Kept subject" and kept["risk_indicators"]==["a","b","c"]
    # tolerant extraction salvages JSON from fenced / prose-wrapped text and never raises
    assert providers._extract_json("```json\n{\"subject\":\"x\"}\n```")=={"subject":"x"}
    assert providers._extract_json("garbage, no json here")=={}

def test_analytics_risk_map(client):
    # Week 4: /analytics is a role + department human-risk map with an engagement
    # funnel and a workforce risk-level distribution.
    e=client.post('/api/v1/employees',json=employee_payload('map@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    sess=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()['session_id']
    for et in ["email_opened","link_clicked","simulation_reported"]:
        client.post(f'/api/v1/simulation/{sess}/event',json={"session_id":sess,"event_type":et})
    a=client.get('/api/v1/analytics').json()
    # funnel is ordered and expressed as % of delivered
    assert [r['stage'] for r in a['funnel']]==["delivered","opened","clicked","submitted","reported"]
    assert a['funnel'][0]['rate']==100.0 and a['funnel'][0]['count']==a['delivered']
    # both dimensions carry the full engagement metric set, keyed by 'key', risk-sorted
    assert a['by_department'] and a['by_role']
    row=next(r for r in a['by_department'] if r['key']==e['department'])
    for k in ('employees','average_risk','delivered','click_rate','submission_rate','reporting_rate','average_response_time_seconds'):
        assert k in row
    assert row['click_rate']==100.0 and row['reporting_rate']==100.0
    risks=[r['average_risk'] for r in a['by_department']]; assert risks==sorted(risks,reverse=True)
    # risk distribution always covers the four ordered levels
    assert [r['level'] for r in a['risk_distribution']]==["critical","high","medium","low"]
    # per-campaign analytics still exposes the flat rate keys
    cid=client.get('/api/v1/campaigns').json()[0]['id']
    assert client.get(f'/api/v1/campaigns/{cid}/analytics').json()['click_rate']==100.0

def test_event_idempotent_and_scenario_result(client):
    # Events are idempotent per (session, event_type); the scenario result reflects
    # the stages reached; a click implies the email was opened.
    e=client.post('/api/v1/employees',json=employee_payload('res@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    sess=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()['session_id']
    r=client.get(f"/api/v1/scenarios/{s['id']}/result").json()
    assert r['launched'] and r['targets'][0]['delivered'] and r['targets'][0]['reached']==[]
    for _ in range(2):  # replay submit — must not double-count
        client.post(f'/api/v1/simulation/{sess}/event',json={"session_id":sess,"event_type":"credential_simulation_submitted"})
    client.post(f'/api/v1/simulation/{sess}/event',json={"session_id":sess,"event_type":"link_clicked"})
    tgt=client.get(f"/api/v1/scenarios/{s['id']}/result").json()['targets'][0]
    assert tgt['submitted'] and tgt['clicked'] and tgt['opened']   # click implies opened
    assert set(tgt['reached'])=={'opened','clicked','submitted'}
    # a terminal response moves the scenario out of ACTIVE into COMPLETED
    assert next(x for x in client.get('/api/v1/scenarios').json() if x['id']==s['id'])['status']=='COMPLETED'
    cid=client.get('/api/v1/campaigns').json()[0]['id']
    assert client.get(f'/api/v1/campaigns/{cid}/analytics').json()['submission_rate']==100.0  # not 200

def test_open_pixel_and_link_retired_after_completion(client):
    e=client.post('/api/v1/employees',json=employee_payload('pixel@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    sess=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()['session_id']
    # the tracking pixel returns a GIF and records email_opened (open, not click)
    px=client.get(f'/api/v1/simulation/{sess}/pixel.gif')
    assert px.status_code==200 and px.headers['content-type']=='image/gif'
    tgt=client.get(f"/api/v1/scenarios/{s['id']}/result").json()['targets'][0]
    assert tgt['opened'] and not tgt['clicked']
    # the landing is live until a terminal action completes it
    assert client.get(f'/api/v1/simulation/{sess}').status_code==200
    client.post(f'/api/v1/simulation/{sess}/event',json={"session_id":sess,"event_type":"simulation_reported"})
    # completed -> the link is retired (410) and no longer serves the lure
    assert client.get(f'/api/v1/simulation/{sess}').status_code==410
    # the scenario list is enriched for the Simulations/Archive split
    row=next(x for x in client.get('/api/v1/scenarios').json() if x['id']==s['id'])
    assert row['completed'] is True and row['department']==e['department']
    assert row['outcome']['reported'] is True and 'reported' in row['outcome']['reached']
    assert row['outcome']['launched_at'] and row['outcome']['recipient_name']==e['full_name']

def test_close_no_response_archives_and_retires_link(client):
    e=client.post('/api/v1/employees',json=employee_payload('close@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"x","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    sess=client.post(f"/api/v1/scenarios/{s['id']}/launch",headers=ADMIN).json()['session_id']
    r=client.post(f"/api/v1/scenarios/{s['id']}/close")       # close as no-response
    assert r.status_code==200 and r.json()['status']=='CLOSED'
    assert client.get(f'/api/v1/simulation/{sess}').status_code==410   # link retired
    row=next(x for x in client.get('/api/v1/scenarios').json() if x['id']==s['id'])
    assert row['status']=='CLOSED' and row['outcome']['launched_at'] and row['outcome']['recipient_name']==e['full_name']
    assert client.post(f"/api/v1/scenarios/{s['id']}/close").status_code==409  # already closed, not ACTIVE
