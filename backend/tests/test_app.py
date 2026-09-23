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
    launch=client.post(f"/api/v1/campaigns/{c['id']}/launch").json(); session=launch['session_id']
    secret='RealPasswordThatMustNeverPersist!123'
    ev=client.post(f'/api/v1/simulation/{session}/event',json={"session_id":session,"event_type":"credential_simulation_submitted","password":secret}).json()
    assert ev['safe_metadata']=={"credential_submitted":True}; assert secret not in str(ev)
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
    assert client.post(f"/api/v1/scenarios/{s['id']}/launch").status_code==409
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    # editing an approved scenario is blocked
    assert client.patch(f"/api/v1/scenarios/{s['id']}",json={"subject":"x"}).status_code==409
    # one-click launch
    launch=client.post(f"/api/v1/scenarios/{s['id']}/launch")
    assert launch.status_code==200
    body=launch.json()
    assert body['session_id'] and body['simulation_url'].endswith('/simulate/'+body['session_id'])

def test_simulation_returns_full_message(client):
    e=client.post('/api/v1/employees',json=employee_payload('sim@demo.example.com')).json()
    s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"awareness","difficulty":"medium"}).json()
    client.post(f"/api/v1/scenarios/{s['id']}/approve")
    launch=client.post(f"/api/v1/scenarios/{s['id']}/launch").json()
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
    assert 'Проверка доступа' in s['email_body']                    # operational context localized, not English
    assert 'password' in s['landing_page_message'].lower()          # safety words retained
    assert 'simulation' in s['landing_page_message'].lower()
    from app.llm import prompts
    assert prompts.normalize_language('ru') == 'ru' and 'Russian' in prompts.LANGUAGES.values()

def test_campaign_requires_approval(client):
    e=client.post('/api/v1/employees',json=employee_payload()).json(); s=client.post('/api/v1/scenarios/generate',json={"employee_id":e['id'],"objective":"awareness","difficulty":"easy"}).json()
    assert client.post('/api/v1/campaigns',json={"scenario_id":s['id'],"name":"Blocked campaign"}).status_code==409
