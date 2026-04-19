from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

import webview


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
DATA_DIR = ROOT / "data"
RUNTIME_CONFIG = DATA_DIR / "runtime-config.json"
WEB_URL = "http://localhost:3000"
API_BASE_URL = "http://localhost:8000/api"
API_READY_URL = "http://localhost:8000/health/ready"

DEFAULT_CONFIG = {
    "wazuh": {
        "credential_name": "Wazuh default credential",
        "connection_mode": "indexer_sync",
        "auth_type": "basic",
        "webhook_secret": "demo-wazuh-secret",
        "manager_url": "",
        "api_url": "",
        "api_username": "",
        "api_password": "",
        "indexer_url": "",
        "indexer_username": "",
        "indexer_password": "",
        "indexer_alert_index": "wazuh-alerts-*",
        "verify_tls": True,
    },
    "velociraptor": {
        "credential_name": "Velociraptor default credential",
        "credential_type": "mock",
        "auth_type": "api_client_config",
        "mode": "mock",
        "transport": "grpc_api",
        "base_url": "https://velociraptor.example.invalid",
        "api_key": "",
        "api_client_config": "",
        "binary_path": "velociraptor",
        "org_id": "root",
        "timeout_seconds": 120,
        "run_path": "/api/v1/collect",
        "status_path": "/api/v1/flows/{flow_id}",
        "results_path": "/api/v1/flows/{flow_id}/results",
        "verify_tls": True,
    },
}

LOCAL_CATALOG = {
    "integrations": [
        {
            "id": "wazuh",
            "name": "Wazuh",
            "description": "Webhook intake and optional manager validation.",
            "category": "siem",
            "tools": ["ingest_wazuh_alert", "test_wazuh_connection"],
            "fields": [
                {"key": "credential_name", "label": "Credential Name", "input": "text", "required": False, "advanced": False, "help_text": "Friendly name shown in CyberRed.", "options": []},
                {"key": "connection_mode", "label": "Connection Mode", "input": "select", "required": True, "advanced": False, "help_text": "Choose how this credential connects.", "options": [{"label": "Webhook only", "value": "webhook_only"}, {"label": "Indexer sync", "value": "indexer_sync"}, {"label": "Manager + Indexer", "value": "manager_and_indexer"}]},
                {"key": "auth_type", "label": "Auth Type", "input": "select", "required": True, "advanced": False, "help_text": "Wazuh APIs use username/password for this MVP.", "options": [{"label": "Username / Password", "value": "basic"}]},
                {"key": "webhook_secret", "label": "Webhook Secret", "input": "password", "advanced": False, "help_text": "Secret used by the webhook.", "options": []},
                {"key": "api_url", "label": "API URL", "input": "text", "advanced": False, "help_text": "Wazuh server API base URL.", "options": []},
                {"key": "api_username", "label": "API Username", "input": "text", "advanced": False, "help_text": "Username used to request a JWT.", "options": []},
                {"key": "api_password", "label": "API Password", "input": "password", "advanced": False, "help_text": "Password used to request a JWT.", "options": []},
                {"key": "indexer_url", "label": "Indexer URL", "input": "text", "advanced": False, "help_text": "Wazuh Indexer/OpenSearch URL for alert sync.", "options": []},
                {"key": "indexer_username", "label": "Indexer Username", "input": "text", "advanced": False, "help_text": "Indexer username.", "options": []},
                {"key": "indexer_password", "label": "Indexer Password", "input": "password", "advanced": False, "help_text": "Indexer password.", "options": []},
                {"key": "indexer_alert_index", "label": "Alert Index Pattern", "input": "text", "advanced": True, "help_text": "Usually wazuh-alerts-*.", "options": []},
                {"key": "verify_tls", "label": "Verify TLS", "input": "checkbox", "advanced": True, "help_text": "Disable only in lab environments.", "options": []},
            ],
        },
        {
            "id": "velociraptor",
            "name": "Velociraptor",
            "description": "Mock or live host triage API.",
            "category": "edr",
            "tools": ["run_process_triage", "run_autoruns_triage", "test_velociraptor_connection"],
            "fields": [
                {"key": "credential_name", "label": "Credential Name", "input": "text", "required": False, "advanced": False, "help_text": "Friendly name shown in CyberRed.", "options": []},
                {"key": "credential_type", "label": "Credential Type", "input": "select", "required": True, "advanced": False, "help_text": "Choose the Velociraptor credential workflow.", "options": [{"label": "Mock demo", "value": "mock"}, {"label": "Live gRPC API", "value": "grpc_api"}, {"label": "HTTP adapter", "value": "http_adapter"}]},
                {"key": "auth_type", "label": "Auth Type", "input": "select", "required": True, "advanced": False, "help_text": "gRPC uses api_client.yaml. HTTP uses bearer token.", "options": [{"label": "API client config", "value": "api_client_config"}, {"label": "Bearer token", "value": "bearer_token"}, {"label": "None / Mock", "value": "none"}]},
                {"key": "mode", "label": "Mode", "input": "select", "advanced": False, "help_text": "Mock or live connector mode.", "options": [{"label": "Mock", "value": "mock"}, {"label": "Live", "value": "live"}]},
                {"key": "transport", "label": "Transport", "input": "select", "advanced": False, "help_text": "Recommended: gRPC API using api_client config.", "options": [{"label": "gRPC API", "value": "grpc_api"}, {"label": "HTTP Adapter", "value": "http"}]},
                {"key": "api_client_config", "label": "API Client Config", "input": "text", "advanced": False, "help_text": "Path to api_client.yaml for gRPC API.", "options": []},
                {"key": "base_url", "label": "Base URL", "input": "text", "advanced": False, "help_text": "Base URL for the live API.", "options": []},
                {"key": "api_key", "label": "API Key", "input": "password", "advanced": False, "help_text": "Bearer token for live mode.", "options": []},
                {"key": "binary_path", "label": "Binary Path", "input": "text", "advanced": True, "help_text": "Usually velociraptor on PATH.", "options": []},
                {"key": "org_id", "label": "Org ID", "input": "text", "advanced": True, "help_text": "Velociraptor org to target.", "options": []},
                {"key": "timeout_seconds", "label": "Timeout Seconds", "input": "text", "advanced": True, "help_text": "How long to wait for flow completion.", "options": []},
                {"key": "run_path", "label": "Run Path", "input": "text", "advanced": True, "help_text": "Relative path for starting a flow.", "options": []},
                {"key": "status_path", "label": "Status Path", "input": "text", "advanced": True, "help_text": "Relative path for checking flow status.", "options": []},
                {"key": "results_path", "label": "Results Path", "input": "text", "advanced": True, "help_text": "Relative path for flow results.", "options": []},
                {"key": "verify_tls", "label": "Verify TLS", "input": "checkbox", "advanced": True, "help_text": "Disable only in lab environments.", "options": []},
            ],
        },
    ],
    "tools": [
        {"id": "get_incident", "name": "Get Incident", "access": "read", "description": "Load incident context."},
        {"id": "summarize_incident", "name": "Summarize Incident", "access": "read", "description": "Create a deterministic summary."},
        {"id": "request_host_triage", "name": "Request Host Triage", "access": "write", "description": "Prepare triage that must be confirmed."},
    ],
    "policies": [
        {"id": "read_auto_execute", "name": "Read Actions Execute Immediately", "scope": "read", "description": "Read-only actions run immediately."},
        {"id": "write_requires_confirmation", "name": "Write Actions Require Confirmation", "scope": "write", "description": "Write actions wait for user approval."},
    ],
}

APP_HTML = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>CyberRed</title><style>
:root{--bg:#efe8df;--panel:#fffaf4;--soft:#f2e6d8;--border:#d8c7b5;--text:#201814;--muted:#70645a;--accent:#9f4124;--blue:#24485c}
*{box-sizing:border-box}body{margin:0;color:var(--text);font-family:Georgia,"Times New Roman",serif;background:radial-gradient(circle at top left,rgba(159,65,36,.14),transparent 30%),radial-gradient(circle at bottom right,rgba(36,72,92,.14),transparent 25%),var(--bg)}
.app{display:grid;grid-template-columns:200px 1fr;min-height:100vh}.sidebar{padding:14px;border-right:1px solid rgba(0,0,0,.08);background:rgba(255,249,243,.72)}.main{padding:14px;display:grid;gap:12px}
.brand,.panel,.toolbar{background:var(--panel);border:1px solid var(--border);border-radius:16px;box-shadow:0 12px 24px rgba(47,31,19,.08)}.brand,.panel{padding:14px}.toolbar{padding:10px 12px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.brand h1,.panel h2,.panel h3{margin:0 0 8px}.brand p,.panel p,.help{color:var(--muted)}.nav,.quick,.list,.feed,.meta{display:grid;gap:8px}
button,input,select,textarea{font:inherit}.nav button,.quick button,.actions button,.toolbar button{border:none;border-radius:12px;padding:9px 11px;cursor:pointer}
.nav button,.quick button,.toolbar button.ghost{background:#fff;border:1px solid var(--border);text-align:left}.nav button.active{background:rgba(159,65,36,.1);color:var(--accent);font-weight:bold}
.actions button,.toolbar button,.send{background:var(--accent);color:#fff}.secondary{background:var(--blue)!important;color:#fff!important}.ghost{background:transparent!important;color:var(--text)!important}
.pill,.tag{display:inline-flex;padding:4px 8px;border-radius:999px;background:var(--soft);font-size:12px;color:var(--muted);margin-right:6px}.ok{color:#2d6a4f}.warn{color:#8a5c12}
.view{display:none}.view.active{display:block}.two{display:grid;grid-template-columns:1.1fr .9fr;gap:12px}.integrations{display:grid;grid-template-columns:310px 1fr;gap:12px}
.item,.msg{border:1px solid var(--border);border-radius:13px;padding:10px;background:rgba(255,255,255,.72)}.item.active{background:rgba(159,65,36,.09);border-color:rgba(159,65,36,.28)}.item strong,.msg .role{display:block;margin-bottom:4px}
.form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.field label{display:block;font-weight:bold;margin-bottom:6px}.field input,.field select,.field textarea{width:100%;padding:9px 10px;border-radius:11px;border:1px solid var(--border);background:#fff}
.field textarea{min-height:92px}.feed{min-height:300px;max-height:360px;overflow:auto;padding-right:2px}.msg.user{background:rgba(36,72,92,.08)}.msg.assistant{background:rgba(159,65,36,.06)}
.chat-layout{display:grid;grid-template-columns:1fr 220px;gap:12px;align-items:start}.chat-main{display:grid;gap:10px}.chat-side{display:grid;gap:10px}.select-card,.note-card{border:1px solid var(--border);border-radius:13px;padding:10px;background:rgba(255,255,255,.68)}
.composer{display:grid;gap:8px}.composer textarea{width:100%;padding:10px 11px;border-radius:12px;border:1px solid var(--border);min-height:82px}.actions{display:flex;flex-wrap:wrap;gap:8px}.log{max-height:150px;overflow:auto;white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px;border:1px solid var(--border);border-radius:13px;padding:9px;background:rgba(255,255,255,.7)}
.setup-card{border:1px solid rgba(36,72,92,.22);border-radius:14px;padding:11px;margin:10px 0 0;background:linear-gradient(135deg,rgba(36,72,92,.08),rgba(159,65,36,.07))}.setup-card strong{display:block;margin-bottom:5px}.setup-card p{margin:0 0 9px}.setup-card button{border:none;border-radius:11px;padding:8px 10px;cursor:pointer;background:#fff;color:var(--text);border:1px solid var(--border)}
.step-list{display:grid;gap:6px;margin:8px 0}.step-list div{display:flex;gap:7px;color:var(--muted);font-size:13px}.step-list b{color:var(--accent)}
.credential-card{border:1px solid var(--border);border-radius:16px;background:rgba(255,255,255,.68);padding:12px;margin-top:10px;display:grid;gap:12px}.credential-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;border-bottom:1px solid rgba(0,0,0,.08);padding-bottom:10px}.credential-top h3{margin:2px 0 0}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.state-badge{border-radius:999px;padding:5px 9px;background:var(--soft);font-size:12px;white-space:nowrap}.state-badge.ok{background:rgba(45,106,79,.12)}.state-badge.warn{background:rgba(138,92,18,.12)}.required-dot{color:var(--accent);margin-left:4px}.field-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end}.mini-button{border:1px solid var(--border);background:#fff!important;color:var(--text)!important;border-radius:10px;padding:8px 9px}.credential-list-title{display:flex;justify-content:space-between;gap:8px;align-items:center}.node-icon{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:9px;background:var(--soft);margin-right:8px;color:var(--accent);font-weight:bold}.item .row-title{display:flex;align-items:center}.item .credential-name{color:var(--muted);font-size:13px;margin-top:3px}.section-label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-top:4px;grid-column:1/-1}.field.wide{grid-column:1/-1}
details{border:1px solid var(--border);border-radius:14px;padding:10px 12px;background:rgba(255,255,255,.66)}summary{cursor:pointer;font-weight:bold}
@media(max-width:1080px){.app,.two,.integrations,.chat-layout{grid-template-columns:1fr}.sidebar{border-right:none;border-bottom:1px solid rgba(0,0,0,.08)}}
</style></head><body><div class="app">
<aside class="sidebar"><div class="brand"><h1>CyberRed</h1><p>Desktop ChatOps client for cyber investigations and guided response.</p></div>
<div class="nav"><button id="nav-chat" class="active" onclick="switchView('chat')">ChatOps</button><button id="nav-home" onclick="switchView('home')">Overview</button><button id="nav-integrations" onclick="switchView('integrations')">Integrations</button></div>
<div class="quick" style="margin-top:18px"><button onclick="runAction('start_stack')">Start Stack</button><button onclick="runAction('validate_all')">Validate All</button><button onclick="runAction('open_workspace')">Open Workspace</button><button onclick="runAction('post_demo_alert')">Post Demo Alert</button><button onclick="runAction('open_logs')">Show Logs</button><button onclick="runAction('stop_stack')">Stop Stack</button></div></aside>
<main class="main"><section class="toolbar"><div><span class="pill" id="status">Ready</span><span class="pill" id="stack-status">Stack not ready</span></div><div class="actions"><button class="ghost" onclick="runAction('refresh_remote')">Refresh</button><button class="ghost" onclick="runAction('reset_defaults')">Reset</button></div></section>
<section id="view-home" class="view"><div class="two"><div class="panel"><h2>Desktop ChatOps</h2><p>Use ChatOps as the primary workflow. Integrations, tools, and policies are shown separately so new connectors can be added later without redesigning the app.</p><div class="meta" id="policy-list"></div></div><div class="panel"><h2>Recent Incidents</h2><p>Select an incident in ChatOps to summarize it or request triage.</p><div class="list" id="incident-list"></div></div></div><div class="panel" style="margin-top:14px"><h2>Available Tools</h2><div class="list" id="tool-list"></div></div></section>
<section id="view-chat" class="view active"><div class="panel"><div class="chat-layout"><div class="chat-main"><h2>ChatOps</h2><div class="feed" id="chat-feed"></div><div class="composer"><textarea id="chat-input" placeholder="Summarize this incident, summarize evidence, or run process triage on this host."></textarea><div class="actions"><button class="send" onclick="sendChat()">Send</button><button id="confirm-button" class="secondary" style="display:none" onclick="confirmPending()">Confirm</button><button class="ghost" onclick="runAction('clear_chat')">Clear</button></div></div></div><div class="chat-side"><div class="select-card"><div class="field"><label for="chat-incident">Incident</label><select id="chat-incident"></select></div></div><div class="note-card"><strong>Quick Actions</strong><div class="actions" style="margin-top:8px"><button onclick="quickChat('Summarize this incident')">Summary</button><button onclick="quickChat('Summarize evidence for this incident')">Evidence</button><button onclick="quickChat('Run process triage on this host')">Process</button><button onclick="quickChat('Run autoruns triage on this host')">Autoruns</button></div></div></div></div></div></section>
<section id="view-integrations" class="view"><div class="integrations"><div class="panel"><div class="credential-list-title"><div><h2>Credentials</h2><p>Pick a connector credential, then configure and test it.</p></div><span class="tag">guided setup</span></div><div class="list" id="integrations-list"></div></div><div class="panel"><h2 id="integration-title">Credential Details</h2><p id="integration-description">Select a credential to configure it.</p><div id="integration-tags"></div><div class="credential-card"><div class="credential-top"><div><span class="eyebrow">Credential</span><h3 id="credential-provider">Select Integration</h3></div><span id="credential-state" class="state-badge warn">not configured</span></div><div class="field wide"><label for="credential-name">Credential name</label><div class="field-row"><input id="credential-name" data-integration="" data-key="credential_name" placeholder="e.g. Production Wazuh" /><button class="mini-button" onclick="fillCredentialName()">Auto name</button></div><div class="help">Give this credential a friendly name, then press Save & Connect.</div></div><div class="section-label">Connection fields</div><div class="form" id="integration-form"></div></div><div id="setup-assistant"></div><div class="actions" style="margin-top:12px"><button id="connect-integration-button" onclick="connectSelectedIntegration()">Save & Connect</button><button class="secondary" onclick="testSelectedIntegration()">Test Only</button><button class="ghost" onclick="saveSelectedIntegration()">Save Only</button></div><div class="log" id="activity-log"></div></div></div></section>
</main></div><script>
const FALLBACK_CATALOG={
integrations:[
{id:'wazuh',name:'Wazuh',description:'Connect Wazuh by webhook, manager API, or indexer sync.',category:'siem',status:'not_configured',tools:['ingest_wazuh_alert','test_wazuh_connection'],config:{credential_name:'Wazuh credential',connection_mode:'indexer_sync',auth_type:'basic',webhook_secret:'demo-wazuh-secret',api_url:'',api_username:'',api_password:'',indexer_url:'',indexer_username:'',indexer_password:'',indexer_alert_index:'wazuh-alerts-*',verify_tls:true},fields:[
{key:'credential_name',label:'Credential Name',input:'text',required:false,advanced:false,help_text:'Friendly name shown in CyberRed.',options:[]},
{key:'connection_mode',label:'Connection Mode',input:'select',required:true,advanced:false,help_text:'Webhook only receives alerts. Indexer sync pulls alerts. Manager + Indexer tests both.',options:[{label:'Indexer sync',value:'indexer_sync'},{label:'Webhook only',value:'webhook_only'},{label:'Manager + Indexer',value:'manager_and_indexer'}]},
{key:'auth_type',label:'Auth Type',input:'select',required:true,advanced:false,help_text:'Wazuh APIs normally use username and password.',options:[{label:'Username / Password',value:'basic'}]},
{key:'webhook_secret',label:'Webhook Secret',input:'password',required:false,advanced:false,help_text:'Secret used when Wazuh sends alerts to CyberRed webhook.',options:[]},
{key:'indexer_url',label:'Indexer URL',input:'text',required:false,advanced:false,help_text:'Example: https://wazuh-indexer:9200',options:[]},
{key:'indexer_username',label:'Indexer Username',input:'text',required:false,advanced:false,help_text:'Example: admin',options:[]},
{key:'indexer_password',label:'Indexer Password',input:'password',required:false,advanced:false,help_text:'Password for Wazuh Indexer/OpenSearch.',options:[]},
{key:'api_url',label:'Manager API URL',input:'text',required:false,advanced:false,help_text:'Example: https://wazuh-manager:55000',options:[]},
{key:'api_username',label:'Manager API Username',input:'text',required:false,advanced:false,help_text:'Example: wazuh-wui',options:[]},
{key:'api_password',label:'Manager API Password',input:'password',required:false,advanced:false,help_text:'Password used to request a Wazuh API token.',options:[]},
{key:'indexer_alert_index',label:'Alert Index Pattern',input:'text',required:false,advanced:true,help_text:'Usually wazuh-alerts-*.',options:[]},
{key:'verify_tls',label:'Verify TLS',input:'checkbox',required:false,advanced:true,help_text:'Disable only in lab environments.',options:[]}]},
{id:'velociraptor',name:'Velociraptor',description:'Connect mock or live Velociraptor triage actions.',category:'edr',status:'not_configured',tools:['run_process_triage','run_autoruns_triage'],config:{credential_name:'Velociraptor credential',credential_type:'mock',auth_type:'none',mode:'mock',transport:'grpc_api',api_client_config:'',base_url:'',api_key:'',binary_path:'velociraptor',org_id:'root',timeout_seconds:'120',run_path:'/api/v1/collect',status_path:'/api/v1/flows/{flow_id}',results_path:'/api/v1/flows/{flow_id}/results',verify_tls:true},fields:[
{key:'credential_name',label:'Credential Name',input:'text',required:false,advanced:false,help_text:'Friendly name shown in CyberRed.',options:[]},
{key:'credential_type',label:'Credential Type',input:'select',required:true,advanced:false,help_text:'Choose mock demo, gRPC API, or HTTP adapter.',options:[{label:'Mock demo',value:'mock'},{label:'Live gRPC API',value:'grpc_api'},{label:'HTTP adapter',value:'http_adapter'}]},
{key:'auth_type',label:'Auth Type',input:'select',required:true,advanced:false,help_text:'gRPC uses api_client.yaml. HTTP uses bearer token.',options:[{label:'None / Mock',value:'none'},{label:'API client config',value:'api_client_config'},{label:'Bearer token',value:'bearer_token'}]},
{key:'mode',label:'Mode',input:'select',required:false,advanced:false,help_text:'Mock or live connector mode.',options:[{label:'Mock',value:'mock'},{label:'Live',value:'live'}]},
{key:'transport',label:'Transport',input:'select',required:false,advanced:false,help_text:'Recommended: gRPC API using api_client config.',options:[{label:'gRPC API',value:'grpc_api'},{label:'HTTP Adapter',value:'http'}]},
{key:'api_client_config',label:'API Client Config',input:'text',required:false,advanced:false,help_text:'Path to api_client.yaml for gRPC API.',options:[]},
{key:'base_url',label:'Base URL',input:'text',required:false,advanced:false,help_text:'Base URL for the live API or adapter.',options:[]},
{key:'api_key',label:'API Key',input:'password',required:false,advanced:false,help_text:'Bearer token for HTTP adapter mode.',options:[]},
{key:'binary_path',label:'Binary Path',input:'text',required:false,advanced:true,help_text:'Usually velociraptor on PATH.',options:[]},
{key:'org_id',label:'Org ID',input:'text',required:false,advanced:true,help_text:'Velociraptor org to target.',options:[]},
{key:'timeout_seconds',label:'Timeout Seconds',input:'text',required:false,advanced:true,help_text:'How long to wait for flow completion.',options:[]},
{key:'run_path',label:'Run Path',input:'text',required:false,advanced:true,help_text:'Relative path for starting a flow.',options:[]},
{key:'status_path',label:'Status Path',input:'text',required:false,advanced:true,help_text:'Relative path for checking flow status.',options:[]},
{key:'results_path',label:'Results Path',input:'text',required:false,advanced:true,help_text:'Relative path for flow results.',options:[]},
{key:'verify_tls',label:'Verify TLS',input:'checkbox',required:false,advanced:true,help_text:'Disable only in lab environments.',options:[]}]}
],
tools:[{id:'get_incident',name:'Get Incident',access:'read',description:'Load incident context.'},{id:'summarize_incident',name:'Summarize Incident',access:'read',description:'Create a deterministic summary.'},{id:'request_host_triage',name:'Request Host Triage',access:'write',description:'Prepare triage that must be confirmed.'}],
policies:[{id:'read_auto_execute',name:'Read Actions Execute Immediately',scope:'read',description:'Read-only actions run immediately.'},{id:'write_requires_confirmation',name:'Write Actions Require Confirmation',scope:'write',description:'Write actions wait for user approval.'}]};
let state={catalog:FALLBACK_CATALOG,incidents:[],chat_history:[],pending_command_audit_id:null,selected_integration_id:'wazuh',stack_ready:false,logs:['[INFO] Local credential form loaded']};
function switchView(v){['home','chat','integrations'].forEach(n=>{document.getElementById(`view-${n}`).classList.toggle('active',n===v);document.getElementById(`nav-${n}`).classList.toggle('active',n===v)})}
function escapeHtml(t){return (t||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('\\n','<br />')}
function selectedIncidentId(){return document.getElementById('chat-incident').value||null}
function collectIntegrationConfig(id){const cfg={};document.querySelectorAll(`[data-integration="${id}"]`).forEach(el=>{const key=el.getAttribute('data-key');cfg[key]=el.type==='checkbox'?el.checked:el.value});return cfg}
function collectAllConfig(){const cfg={};(state.catalog.integrations||[]).forEach(i=>cfg[i.id]=Object.assign({},i.config||{}));document.querySelectorAll('[data-integration]').forEach(el=>{const id=el.getAttribute('data-integration');const key=el.getAttribute('data-key');cfg[id]=cfg[id]||{};cfg[id][key]=el.type==='checkbox'?el.checked:el.value});return cfg}
function normalizeState(next){const merged=Object.assign({},state,next||{});if(!merged.catalog||!(merged.catalog.integrations||[]).length){merged.catalog=FALLBACK_CATALOG}if(!merged.selected_integration_id){merged.selected_integration_id='wazuh'}return merged}
function renderState(next){state=normalizeState(next);document.getElementById('status').innerText=state.status||'Ready';document.getElementById('stack-status').innerText=state.stack_ready?'Stack ready':'Stack not ready';document.getElementById('activity-log').innerText=(state.logs||[]).join('\\n');renderHome();renderIntegrations();renderChat()}
function renderHome(){const incidents=document.getElementById('incident-list');incidents.innerHTML='';if(!(state.incidents||[]).length){incidents.innerHTML='<div class="item"><strong>No incidents yet</strong><div>Post a demo alert or ingest a Wazuh alert first.</div></div>'}else{state.incidents.slice(0,6).forEach(i=>{const el=document.createElement('div');el.className='item';el.innerHTML=`<strong>${i.title}</strong><span class="tag">${i.status}</span><span class="tag">${i.severity}</span>`;incidents.appendChild(el)})}const tools=document.getElementById('tool-list');tools.innerHTML='';(state.catalog.tools||[]).forEach(t=>{const el=document.createElement('div');el.className='item';el.innerHTML=`<strong>${t.name}</strong><span class="tag ${t.access==='write'?'warn':'ok'}">${t.access}</span><div>${t.description}</div>`;tools.appendChild(el)});const policies=document.getElementById('policy-list');policies.innerHTML='';(state.catalog.policies||[]).forEach(p=>{const el=document.createElement('div');el.className='item';el.innerHTML=`<strong>${p.name}</strong><span class="tag">${p.scope}</span><div>${p.description}</div>`;policies.appendChild(el)})}
function buildField(integrationId,config,field){const wrap=document.createElement('div');wrap.className=`field ${['webhook_secret','api_url','manager_url','indexer_url','api_client_config','base_url'].includes(field.key)?'wide':''}`;const label=document.createElement('label');label.innerHTML=`${field.label}${field.required?'<span class="required-dot">*</span>':''}`;wrap.appendChild(label);let input;if(field.input==='select'){input=document.createElement('select');(field.options||[]).forEach(opt=>{const o=document.createElement('option');o.value=opt.value;o.innerText=opt.label;input.appendChild(o)});input.value=config[field.key]||(field.options[0]?field.options[0].value:'')}else{input=document.createElement('input');input.type=field.input==='checkbox'?'checkbox':field.input;if(field.input==='checkbox'){input.checked=config[field.key]!==false}else{input.value=config[field.key]??'';if(field.placeholder)input.placeholder=field.placeholder}}input.setAttribute('data-integration',integrationId);input.setAttribute('data-key',field.key);wrap.appendChild(input);if(field.help_text){const help=document.createElement('div');help.className='help';help.innerText=field.help_text;wrap.appendChild(help)}return wrap}
function setFieldValue(id,key,value){const el=document.querySelector(`[data-integration="${id}"][data-key="${key}"]`);if(!el)return;if(el.type==='checkbox'){el.checked=Boolean(value)}else{el.value=value}}
function fillCredentialName(){const id=state.selected_integration_id;if(!id)return;const selected=(state.catalog.integrations||[]).find(i=>i.id===id);const suffix=new Date().toLocaleDateString();setFieldValue(id,'credential_name',`${selected?selected.name:id} credential ${suffix}`)}
function applyPreset(name){const id=state.selected_integration_id;if(!id)return;const presets={wazuh:{demo:{credential_name:'Wazuh webhook demo',connection_mode:'webhook_only',auth_type:'basic',webhook_secret:'demo-wazuh-secret',api_url:'',api_username:'',api_password:'',indexer_url:'',indexer_username:'',indexer_password:'',indexer_alert_index:'wazuh-alerts-*',verify_tls:true},local:{credential_name:'Local Wazuh lab',connection_mode:'indexer_sync',auth_type:'basic',webhook_secret:'demo-wazuh-secret',api_url:'https://localhost:55000',api_username:'wazuh-wui',api_password:'',indexer_url:'https://localhost:9200',indexer_username:'admin',indexer_password:'',indexer_alert_index:'wazuh-alerts-*',verify_tls:false},cloud:{credential_name:'Production Wazuh',connection_mode:'manager_and_indexer',auth_type:'basic',webhook_secret:'demo-wazuh-secret',api_url:'https://YOUR-WAZUH-MANAGER:55000',api_username:'wazuh-wui',api_password:'',indexer_url:'https://YOUR-WAZUH-INDEXER:9200',indexer_username:'admin',indexer_password:'',indexer_alert_index:'wazuh-alerts-*',verify_tls:true}},velociraptor:{mock:{credential_name:'Velociraptor mock demo',credential_type:'mock',auth_type:'none',mode:'mock',transport:'grpc_api',api_client_config:'',base_url:'',api_key:'',binary_path:'velociraptor',org_id:'root',timeout_seconds:'120',run_path:'/api/v1/collect',status_path:'/api/v1/flows/{flow_id}',results_path:'/api/v1/flows/{flow_id}/results',verify_tls:true},grpc:{credential_name:'Velociraptor gRPC live',credential_type:'grpc_api',auth_type:'api_client_config',mode:'live',transport:'grpc_api',api_client_config:'C:\\\\Velociraptor\\\\api_client.yaml',base_url:'',api_key:'',binary_path:'velociraptor',org_id:'root',timeout_seconds:'120',run_path:'/api/v1/collect',status_path:'/api/v1/flows/{flow_id}',results_path:'/api/v1/flows/{flow_id}/results',verify_tls:true},http:{credential_name:'Velociraptor HTTP adapter',credential_type:'http_adapter',auth_type:'bearer_token',mode:'live',transport:'http',api_client_config:'',base_url:'https://YOUR-VELOCIRAPTOR-ADAPTER',api_key:'',binary_path:'velociraptor',org_id:'root',timeout_seconds:'120',run_path:'/api/v1/collect',status_path:'/api/v1/flows/{flow_id}',results_path:'/api/v1/flows/{flow_id}/results',verify_tls:true}}};Object.entries((presets[id]||{})[name]||{}).forEach(([k,v])=>setFieldValue(id,k,v));document.getElementById('status').innerText=`Preset applied: ${id} / ${name}`}
function setupAssistantHtml(selected){if(!selected)return'';if(selected.id==='wazuh'){return `<div class="setup-card"><strong>Easy Wazuh credential</strong><p>เลือก preset เหมือน n8n credential แล้วเติม password/token ของจริง จากนั้นกด Save & Connect</p><div class="actions"><button onclick="applyPreset('demo')">Webhook Demo</button><button onclick="applyPreset('local')">Local Lab</button><button onclick="applyPreset('cloud')">Live / Cloud</button></div><div class="step-list"><div><b>1</b> ตั้งชื่อ credential</div><div><b>2</b> ใส่ Indexer URL + Username + Password เพื่อดึง alert ย้อนหลัง</div><div><b>3</b> กด Save & Connect เพื่อ save + test + sync</div></div></div>`}if(selected.id==='velociraptor'){return `<div class="setup-card"><strong>Easy Velociraptor credential</strong><p>เริ่มจาก Mock ถ้าจะ demo ทันที หรือเลือก Live gRPC/HTTP เมื่อต้องต่อของจริง</p><div class="actions"><button onclick="applyPreset('mock')">Demo Mock</button><button onclick="applyPreset('grpc')">Live gRPC</button><button onclick="applyPreset('http')">HTTP Adapter</button></div><div class="step-list"><div><b>1</b> ตั้งชื่อ credential</div><div><b>2</b> Mock ใช้ได้ทันที ไม่ต้องมี credential</div><div><b>3</b> Live gRPC ใส่ api_client.yaml หรือ HTTP ใส่ Base URL + API Key</div></div></div>`}return''}
function renderIntegrations(){const list=document.getElementById('integrations-list');list.innerHTML='';const items=state.catalog.integrations||[];if(!state.selected_integration_id&&items.length){state.selected_integration_id=items[0].id}items.forEach(integration=>{const cfg=integration.config||{};const el=document.createElement('div');el.className=`item ${integration.id===state.selected_integration_id?'active':''}`;el.onclick=()=>{state.selected_integration_id=integration.id;renderIntegrations()};el.innerHTML=`<div class="row-title"><span class="node-icon">${integration.name.slice(0,1)}</span><strong>${integration.name}</strong></div><div class="credential-name">${cfg.credential_name||`${integration.name} credential`}</div><div style="margin-top:8px"><span class="tag">${integration.category}</span><span class="tag ${integration.status==='configured'?'ok':'warn'}">${integration.status}</span></div>`;list.appendChild(el)});const selected=items.find(i=>i.id===state.selected_integration_id);const config=(selected&&selected.config)||{};document.getElementById('integration-title').innerText=selected?selected.name:'Integration Details';document.getElementById('integration-description').innerText=selected?selected.description:'Select an integration to configure it.';document.getElementById('integration-tags').innerHTML=selected?`<span class="tag">${selected.category}</span><span class="tag">${selected.tools.length} tools</span><span class="tag ${selected.status==='configured'?'ok':'warn'}">${selected.status}</span>`:'';document.getElementById('setup-assistant').innerHTML=setupAssistantHtml(selected);document.getElementById('connect-integration-button').style.display=selected?'inline-flex':'none';document.getElementById('credential-provider').innerText=selected?`${selected.name} credential`:'Select Integration';const badge=document.getElementById('credential-state');badge.className=`state-badge ${selected&&selected.status==='configured'?'ok':'warn'}`;badge.innerText=selected&&selected.status==='configured'?'configured':'not configured';const nameInput=document.getElementById('credential-name');nameInput.setAttribute('data-integration',selected?selected.id:'');nameInput.value=config.credential_name||`${selected?selected.name:'Integration'} credential`;const form=document.getElementById('integration-form');form.innerHTML='';if(!selected)return;selected.fields.filter(f=>!f.advanced&&f.key!=='credential_name').forEach(f=>form.appendChild(buildField(selected.id,config,f)));const advanced=selected.fields.filter(f=>f.advanced&&f.key!=='credential_name');if(advanced.length){const details=document.createElement('details');details.innerHTML='<summary>Advanced Settings</summary>';advanced.forEach(f=>details.appendChild(buildField(selected.id,config,f)));form.appendChild(details)}}
function renderChat(){const select=document.getElementById('chat-incident');const current=select.value;select.innerHTML='<option value="">Choose incident</option>';(state.incidents||[]).forEach(i=>{const o=document.createElement('option');o.value=i.id;o.innerText=`${i.title} (${i.status})`;select.appendChild(o)});if((state.incidents||[]).some(i=>i.id===current)){select.value=current}const feed=document.getElementById('chat-feed');feed.innerHTML='';if(!(state.chat_history||[]).length){feed.innerHTML='<div class="msg assistant"><div class="role">assistant</div><div>Ask for an incident summary, an evidence summary, or request triage for the selected incident.</div></div>'}else{state.chat_history.forEach(m=>{const el=document.createElement('div');el.className=`msg ${m.role}`;el.innerHTML=`<div class="role">${m.role}</div><div>${escapeHtml(m.content)}</div>${m.mode?`<div class="help">mode: ${m.mode}</div>`:''}${m.command_audit_id?`<div class="help">command audit: ${m.command_audit_id}</div>`:''}`;feed.appendChild(el)})}feed.scrollTop=feed.scrollHeight;document.getElementById('confirm-button').style.display=state.pending_command_audit_id?'inline-flex':'none'}
async function refreshState(){try{if(!window.pywebview||!window.pywebview.api){renderState(state);return}renderState(await window.pywebview.api.get_state())}catch(e){state.logs=[...(state.logs||[]),`[WARN] UI fallback active: ${e}`].slice(-80);renderState(state)}}
async function runAction(action){await window.pywebview.api.run_action(action,collectAllConfig());await refreshState()}
async function saveSelectedIntegration(){if(!state.selected_integration_id)return;await window.pywebview.api.save_integration(state.selected_integration_id,collectIntegrationConfig(state.selected_integration_id));await refreshState()}
async function testSelectedIntegration(){if(!state.selected_integration_id)return;await window.pywebview.api.test_integration(state.selected_integration_id,collectIntegrationConfig(state.selected_integration_id));await refreshState()}
async function connectSelectedIntegration(){if(!state.selected_integration_id)return;document.getElementById('status').innerText='Connecting...';await window.pywebview.api.connect_integration(state.selected_integration_id,collectIntegrationConfig(state.selected_integration_id));await refreshState()}
async function sendChat(){const text=document.getElementById('chat-input').value.trim();if(!text)return;await window.pywebview.api.send_chat(text,selectedIncidentId());document.getElementById('chat-input').value='';await refreshState();switchView('chat')}
async function quickChat(text){document.getElementById('chat-input').value=text;await sendChat()}
async function confirmPending(){if(!state.pending_command_audit_id)return;await window.pywebview.api.confirm_pending_action(state.pending_command_audit_id);await refreshState()}
document.addEventListener('DOMContentLoaded',()=>{renderState(state);switchView('integrations')})
window.addEventListener('pywebviewready',async()=>{await refreshState();setInterval(refreshState,1800)})
</script></body></html>
"""


class DesktopApi:
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.status = "Ready"
        self.window: webview.Window | None = None
        self.chat_history: list[dict[str, Any]] = []
        self.pending_command_audit_id: str | None = None
        self.catalog_cache = self._local_catalog()
        self.incidents_cache: list[dict[str, Any]] = []
        self.stack_ready = False
        self.selected_integration_id = "wazuh"

    def log(self, message: str) -> None:
        self.logs.append(message)
        self.logs = self.logs[-250:]
        self.status = message

    def get_state(self) -> dict[str, Any]:
        self._refresh_remote_state()
        return {
            "status": self.status,
            "logs": self.logs,
            "catalog": self.catalog_cache,
            "incidents": self.incidents_cache,
            "chat_history": self.chat_history,
            "pending_command_audit_id": self.pending_command_audit_id,
            "selected_integration_id": self.selected_integration_id,
            "stack_ready": self.stack_ready,
        }

    def run_action(self, action: str, config: dict[str, Any]) -> dict[str, Any]:
        threading.Thread(target=self._dispatch_action, args=(action, config), daemon=True).start()
        return {"ok": True}

    def save_integration(self, integration_id: str, config: dict[str, Any]) -> dict[str, Any]:
        threading.Thread(target=self._save_integration, args=(integration_id, config), daemon=True).start()
        return {"ok": True}

    def test_integration(self, integration_id: str, config: dict[str, Any]) -> dict[str, Any]:
        threading.Thread(target=self._test_integration, args=(integration_id, config), daemon=True).start()
        return {"ok": True}

    def connect_integration(self, integration_id: str, config: dict[str, Any]) -> dict[str, Any]:
        threading.Thread(target=self._connect_integration, args=(integration_id, config), daemon=True).start()
        return {"ok": True}

    def send_chat(self, message: str, incident_id: str | None) -> dict[str, Any]:
        threading.Thread(target=self._send_chat, args=(message, incident_id), daemon=True).start()
        return {"ok": True}

    def confirm_pending_action(self, command_audit_id: str) -> dict[str, Any]:
        threading.Thread(target=self._confirm_pending_action, args=(command_audit_id,), daemon=True).start()
        return {"ok": True}

    def _dispatch_action(self, action: str, config: dict[str, Any]) -> None:
        try:
            actions = {
                "start_stack": lambda: self.start_stack(config),
                "stop_stack": self.stop_stack,
                "post_demo_alert": lambda: self.post_demo_alert(config),
                "open_workspace": lambda: self.open_workspace(config),
                "validate_all": lambda: self.validate_all(config),
                "open_logs": self.open_logs,
                "clear_chat": self.clear_chat,
                "reset_defaults": self.reset_defaults,
                "refresh_remote": self._refresh_remote_state,
                "save_settings": lambda: self.save_settings(config),
            }
            handler = actions.get(action)
            if handler is None:
                raise RuntimeError(f"Unsupported action: {action}")
            handler()
        except Exception as exc:
            self.log(f"[ERROR] {exc}")

    def ensure_docker(self) -> None:
        if shutil.which("docker") is None:
            raise RuntimeError("Docker CLI was not found in PATH.")
        subprocess.run(["docker", "info"], cwd=ROOT, check=True, capture_output=True, text=True)

    def ensure_env_file(self) -> None:
        if ENV_FILE.exists():
            self.log("[OK] Existing .env found")
            return
        if ENV_EXAMPLE.exists():
            shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
            self.log("[OK] Created .env from .env.example")

    def load_settings(self) -> dict[str, Any]:
        if not RUNTIME_CONFIG.exists():
            return json.loads(json.dumps(DEFAULT_CONFIG))
        return self._normalized_config(json.loads(RUNTIME_CONFIG.read_text(encoding="utf-8")))

    def save_settings(self, config: dict[str, Any]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        merged = self._normalized_config(config)
        RUNTIME_CONFIG.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        self.catalog_cache = self._local_catalog()
        self.log("[OK] Integration settings saved")

    def reset_defaults(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RUNTIME_CONFIG.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        self.catalog_cache = self._local_catalog()
        self.log("[OK] Integration settings reset to defaults")

    def start_stack(self, config: dict[str, Any]) -> None:
        self.log("[STEP] Checking Docker...")
        self.ensure_docker()
        self.ensure_env_file()
        self.save_settings(config)
        self.log("[STEP] Building and starting containers...")
        subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=ROOT, check=True)
        self.wait_for_http(API_READY_URL)
        self.wait_for_http(WEB_URL)
        self.stack_ready = True
        self._refresh_remote_state()
        self.log("[OK] Stack is ready")

    def ensure_stack_running(self, config: dict[str, Any]) -> None:
        if self._api_is_ready():
            self.stack_ready = True
            return
        self.log("[STEP] Starting containers...")
        self.ensure_docker()
        self.ensure_env_file()
        self.save_settings(config)
        subprocess.run(["docker", "compose", "up", "-d"], cwd=ROOT, check=True)
        self.wait_for_http(API_READY_URL)
        self.wait_for_http(WEB_URL)
        self.stack_ready = True

    def validate_all(self, config: dict[str, Any]) -> None:
        self.ensure_stack_running(config)
        checks = []
        for service in ["wazuh", "velociraptor"]:
            try:
                response = self._request_json("/settings/integrations/test", method="POST", data={"service": service})
                checks.append(f"{service}: OK - {response.get('detail', 'success')}")
            except Exception as exc:
                checks.append(f"{service}: FAILED - {exc}")
        self._refresh_remote_state()
        self.log("[CHECK] " + " | ".join(checks))

    def open_logs(self) -> None:
        self.ensure_docker()
        completed = subprocess.run(
            ["docker", "compose", "logs", "--tail", "80"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        lines = completed.stdout.splitlines()[-80:]
        for line in lines:
            self.log(line)

    def clear_chat(self) -> None:
        self.chat_history = []
        self.pending_command_audit_id = None
        self.log("[OK] Chat cleared")

    def stop_stack(self) -> None:
        self.log("[STEP] Stopping containers...")
        subprocess.run(["docker", "compose", "down"], cwd=ROOT, check=True)
        self.stack_ready = False
        self.incidents_cache = []
        self.catalog_cache = self._local_catalog()
        self.log("[OK] Stack stopped")

    def post_demo_alert(self, config: dict[str, Any]) -> None:
        self.save_settings(config)
        self.wait_for_http(API_READY_URL)
        body = (ROOT / "sample-data" / "wazuh-alert.json").read_text(encoding="utf-8")
        secret = ((config.get("wazuh") or {}).get("webhook_secret") or "demo-wazuh-secret").strip()
        request = urllib.request.Request(
            f"{API_BASE_URL}/wazuh/alerts",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Webhook-Secret": secret},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        self._refresh_remote_state()
        self.log("[OK] Demo alert posted")

    def open_workspace(self, config: dict[str, Any]) -> None:
        self.start_stack(config)
        self.log("[STEP] Opening workspace...")
        try:
            webview.create_window("CyberRed Workspace", WEB_URL, width=1440, height=900)
        except Exception:
            webbrowser.open(WEB_URL)
            self.log("[WARN] Embedded workspace window failed, opened default browser instead")

    def wait_for_http(self, url: str, timeout_seconds: int = 180) -> None:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if 200 <= response.status < 400:
                        return
            except Exception:
                time.sleep(2)
        raise RuntimeError(f"Timed out waiting for {url}")

    def _save_integration(self, integration_id: str, config: dict[str, Any]) -> None:
        all_config = self.load_settings()
        all_config[integration_id] = config
        self.save_settings(all_config)
        self.selected_integration_id = integration_id
        if self._api_is_ready():
            self._request_json(f"/settings/integrations/{integration_id}/config", method="PUT", data={"config": config})
            self._refresh_remote_state()
        self.log(f"[OK] {integration_id} settings saved")

    def _test_integration(self, integration_id: str, config: dict[str, Any]) -> None:
        self._save_integration(integration_id, config)
        if not self._api_is_ready():
            self.log("[WARN] Start the stack before testing integrations.")
            return
        self.wait_for_http(API_READY_URL)
        response = self._request_json("/settings/integrations/test", method="POST", data={"service": integration_id})
        self.log(f"[OK] {integration_id} connection test passed: {response.get('detail', 'success')}")

    def _connect_integration(self, integration_id: str, config: dict[str, Any]) -> None:
        self.selected_integration_id = integration_id
        all_config = self.load_settings()
        all_config[integration_id] = config
        self.ensure_stack_running(all_config)
        payload = {
            "config": config,
            "sync_alerts": integration_id == "wazuh",
            "sync_limit": int(config.get("sync_limit") or 25),
        }
        response = self._request_json(
            f"/settings/integrations/{integration_id}/connect",
            method="POST",
            data=payload,
            timeout=60,
        )
        self._refresh_remote_state()
        if integration_id == "wazuh":
            sync = response.get("sync") or {}
            self.log(
                f"[OK] Wazuh connected. Imported {sync.get('imported', 0)} alert(s), "
                f"skipped {sync.get('skipped', 0)}."
            )
            return
        self.log(f"[OK] {integration_id} connected: {response.get('message', 'success')}")

    def _send_chat(self, message: str, incident_id: str | None) -> None:
        try:
            if not self._api_is_ready():
                self.chat_history.append({"role": "assistant", "content": "Start the stack first, then send the command again.", "mode": "not_ready"})
                self.log("[WARN] Chat requires the stack to be running.")
                return
            self.chat_history.append({"role": "user", "content": message})
            payload: dict[str, Any] = {"message": message, "user_id": "desktop-user"}
            if incident_id:
                payload["incident_id"] = incident_id
            response = self._request_json("/chat", method="POST", data=payload)
            self.chat_history.append(
                {
                    "role": "assistant",
                    "content": response.get("response", ""),
                    "mode": response.get("mode"),
                    "command_audit_id": response.get("command_audit_id"),
                }
            )
            self.pending_command_audit_id = response.get("command_audit_id")
            self.log("[OK] Chat response received")
        except Exception as exc:
            self.chat_history.append({"role": "assistant", "content": f"Error: {exc}", "mode": "error"})
            self.log(f"[ERROR] {exc}")

    def _confirm_pending_action(self, command_audit_id: str) -> None:
        try:
            if not self._api_is_ready():
                self.chat_history.append({"role": "assistant", "content": "Start the stack before confirming this action.", "mode": "not_ready"})
                self.log("[WARN] Confirmation requires the stack to be running.")
                return
            response = self._request_json(
                "/triage/confirm",
                method="POST",
                data={"command_audit_id": command_audit_id, "approved_by": "desktop-user"},
            )
            self.chat_history.append({"role": "assistant", "content": f"Triage executed. Job {response.get('job_id')} created.", "mode": "write_executed"})
            self.pending_command_audit_id = None
            self._refresh_remote_state()
            self.log("[OK] Pending action confirmed")
        except Exception as exc:
            self.chat_history.append({"role": "assistant", "content": f"Confirmation failed: {exc}", "mode": "error"})
            self.log(f"[ERROR] {exc}")

    def _refresh_remote_state(self) -> None:
        self.stack_ready = self._api_is_ready()
        if not self.stack_ready:
            self.catalog_cache = self._local_catalog()
            return
        try:
            self.catalog_cache = self._merge_catalog_defaults(self._request_json("/settings/catalog"))
            self.incidents_cache = self._request_json("/incidents")
        except Exception as exc:
            self.catalog_cache = self._local_catalog()
            self.log(f"[WARN] Remote state refresh failed: {exc}")

    def _request_json(self, path: str, *, method: str = "GET", data: dict[str, Any] | None = None, timeout: int = 20) -> Any:
        headers = {"X-Internal-Api-Key": self._internal_api_key()}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(f"{API_BASE_URL}{path}", data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8") or "{}"
        except urllib.error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8") or exc.reason) from exc
        return json.loads(raw)

    def _internal_api_key(self) -> str:
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("INTERNAL_API_KEY="):
                    return line.split("=", 1)[1].strip()
        return "demo-internal-key"

    def _api_is_ready(self) -> bool:
        try:
            with urllib.request.urlopen(API_READY_URL, timeout=2) as response:
                return 200 <= response.status < 400
        except Exception:
            return False

    def _local_catalog(self) -> dict[str, Any]:
        config = self.load_settings()
        catalog = json.loads(json.dumps(LOCAL_CATALOG))
        for integration in catalog["integrations"]:
            current = config.get(integration["id"], {}) or {}
            integration["config"] = current
            integration["status"] = "configured" if any(bool(current.get(field["key"])) for field in integration["fields"] if field["input"] != "checkbox") else "not_configured"
            integration["enabled"] = True
        return catalog

    def _merge_catalog_defaults(self, remote_catalog: dict[str, Any]) -> dict[str, Any]:
        local = self._local_catalog()
        local_by_id = {item["id"]: item for item in local.get("integrations", [])}
        merged = json.loads(json.dumps(remote_catalog or {}))
        integrations = []
        seen_ids: set[str] = set()
        for remote in merged.get("integrations", []) or []:
            integration_id = remote.get("id")
            fallback = local_by_id.get(integration_id, {})
            combined = json.loads(json.dumps(fallback))
            combined.update({key: value for key, value in remote.items() if value not in (None, "")})
            if not combined.get("fields"):
                combined["fields"] = fallback.get("fields", [])
            if not combined.get("config"):
                combined["config"] = fallback.get("config", {})
            integrations.append(combined)
            seen_ids.add(integration_id)
        for integration_id, fallback in local_by_id.items():
            if integration_id not in seen_ids:
                integrations.append(fallback)
        merged["integrations"] = integrations
        merged.setdefault("tools", local.get("tools", []))
        merged.setdefault("policies", local.get("policies", []))
        return merged

    def _normalized_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        for section, values in (config or {}).items():
            if isinstance(values, dict):
                merged.setdefault(section, {})
                for key, value in values.items():
                    merged[section][key] = value.strip() if isinstance(value, str) else value
            else:
                merged[section] = values.strip() if isinstance(values, str) else values
        return merged


def main() -> int:
    api = DesktopApi()
    api.window = webview.create_window("CyberRed", html=APP_HTML, js_api=api, width=1600, height=820, min_size=(1180, 680))
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
