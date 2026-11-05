/* Fresh local presentation records. These are NOT a second
 * AppAI identity, login credentials, authority grants or imported acceptance. */
'use strict';
const fs=require('node:fs'),crypto=require('node:crypto');
const SCOPES=Object.freeze(['project:list','project:read','role:list','role:read',
 'workflow:create','workflow:delete','workflow:export','workflow:import','workflow:list','workflow:read','workflow:update']);
function validate(value){
 if(!value||Object.keys(value).sort().join(',')!=='createdAt,instanceId,projectId,schema,userId'||value.schema!=='studio.editor-owner/1'||
  !/^[a-f0-9]{16}$/.test(value.projectId)||!/^[a-f0-9]{64}$/.test(value.instanceId)||
  !/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(value.userId)||!Number.isFinite(Date.parse(value.createdAt)))throw Error('INVALID_LOCAL_PRESENTATION_IDENTITY');
 return value;
}
function read(file){
 const stat=fs.lstatSync(file);
 if(!stat.isFile()||stat.isSymbolicLink()||stat.size>4096)throw Error('INVALID_LOCAL_PRESENTATION_FILE');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
 try{
  const before=fs.fstatSync(fd);
  if(!before.isFile()||before.dev!==stat.dev||before.ino!==stat.ino||before.size!==stat.size)throw Error('INVALID_LOCAL_PRESENTATION_FILE');
  const bytes=Buffer.alloc(before.size+1);let length=0;
  while(length<bytes.length){const n=fs.readSync(fd,bytes,length,bytes.length-length,null);if(!n)break;length+=n;}
  const after=fs.fstatSync(fd),current=fs.lstatSync(file);
  if(length!==before.size||after.size!==before.size||current.isSymbolicLink()||current.dev!==before.dev||current.ino!==before.ino||current.size!==before.size)throw Error('INVALID_LOCAL_PRESENTATION_FILE');
  let value;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,length)));}catch{throw Error('INVALID_LOCAL_PRESENTATION_FILE');}
  return validate(value);
 }finally{fs.closeSync(fd);}
}
function initialize(file,{reviewed=false}={}){
 if(!reviewed)throw Error('OWNER_REVIEW_REQUIRED');
 if(fs.existsSync(file))return read(file);
 const value={schema:'studio.editor-owner/1',userId:crypto.randomUUID(),projectId:crypto.randomBytes(8).toString('hex'),instanceId:crypto.randomBytes(32).toString('hex'),createdAt:new Date().toISOString()};
 const fd=fs.openSync(file,'wx',0o600);
 try{fs.writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
 return validate(value);
}
function project({identity,settingsTemplate,port}){
 identity=validate(structuredClone(identity));
 if(!Number.isInteger(port)||port<1024||port>65535)throw Error('INVALID_LOCAL_PORT');
 const scopes=[...SCOPES],at=identity.createdAt;
 const user={kind:'human',createdAt:at,id:identity.userId,email:'owner@localhost.invalid',firstName:'Local',lastName:'Studio',
  personalizationAnswers:null,settings:{userActivated:true},disabled:false,mfaEnabled:false,lastActiveAt:at,isPending:false,
  role:'global:owner',signInType:'email',isOwner:true,featureFlags:{},featureFlagPayloads:{},globalScopes:scopes,mfaAuthenticated:false};
 const role=(slug,type)=>({updatedAt:at,createdAt:at,slug,displayName:'Local Studio owner',description:'Presentation only; host authorization remains independent.',systemRole:true,roleType:type,scopes:scopes.map(slug=>({slug,displayName:slug,description:null}))});
 const personal={updatedAt:at,createdAt:at,id:identity.projectId,name:'Local Studio',type:'personal',icon:null,description:null,customTelemetryTags:[],creatorId:identity.userId,
  projectRelations:[{updatedAt:at,createdAt:at,userId:identity.userId,projectId:identity.projectId,role:role('project:personalOwner','project')}],scopes,rolesManaged:false};
 const settings=structuredClone(settingsTemplate);
 // These controls describe the existing local compatibility surface. Unknown
 // Community functionality remains mandatory work; no scope is accepted here.
 settings.instanceId=identity.instanceId;settings.nodeJsVersion=process.version;
 settings.urlBaseEditor=`http://127.0.0.1:${port}/`;settings.urlBaseWebhook=`http://127.0.0.1:${port}/webhook/`;settings.urlBaseWebhookTest=`http://127.0.0.1:${port}/webhook-test/`;
 settings.license={consumerId:'',environment:'',planName:'Community'};
 settings.telemetry={enabled:false};settings.posthog={enabled:false,apiHost:'',apiKey:'',autocapture:false,disableSessionRecording:true,proxy:false,debug:false};
 settings.versionNotifications={enabled:false,endpoint:'',whatsNewEnabled:false,whatsNewEndpoint:'',infoUrl:''};
 settings.dynamicBanners={endpoint:'',enabled:false,filters:{}};settings.templates={enabled:false,host:''};settings.hiringBannerEnabled=false;
 settings.userManagement={quota:1,showSetupOnFirstLoad:false,smtpSetup:false,authenticationMethod:'email',passwordMinLength:12};
 settings.publicApi={enabled:false,latestVersion:1,path:'api',swaggerUi:{enabled:false}};
 settings.communityNodesEnabled=false;settings.unverifiedCommunityNodesEnabled=false;settings.communityNodesManagedByEnv=true;
 settings.enterprise=Object.fromEntries(Object.keys(settings.enterprise||{}).map(key=>[key,false]));
 // In the pinned Community protocol this field is a structured quota, not a
 // boolean feature flag. Flattening it breaks the editor's project store.
 settings.enterprise.projects={team:{limit:0}};
 settings.aiAssistant={enabled:false,setup:false,cloudUbbEnabled:false};settings.aiBuilder={enabled:false,setup:false};settings.aiCredits={enabled:false,credits:0,setup:false};
 settings.askAi={enabled:false};settings.ai={allowSendingParameterValues:false};settings.easyAIWorkflowOnboarded=true;
 settings.activeModules=[];settings.allowedModules={};settings.inbox={enabled:false,availableTypes:[],failedTypes:[]};
 settings.oauthCallbackUrls={oauth1:'',oauth2:''};settings.jwksUri='';
 settings.sso={managedByEnv:true,saml:{loginEnabled:false,loginLabel:''},ldap:{loginEnabled:false,loginLabel:''},oidc:{loginEnabled:false,loginLabel:''}};
 const simple=Object.fromEntries(Object.entries(personal).filter(([key])=>!['projectRelations','scopes','rolesManaged'].includes(key)));
 return {user,personal,projects:[simple],myProjects:[{...simple,role:'project:personalOwner',scopes}],projectCount:{personal:1,team:0},
  roles:{global:[role('global:owner','global')],project:[role('project:personalOwner','project')],credential:[],workflow:[]},settings,
  capabilities:{status:'BUILDING_NOT_ACCEPTED',supported:['workflow-drafts','resident-body-view'],unavailable:['workflow-execution','credential-management','settings-mutation'],authority:'NONE'}};
}
module.exports={initialize,read,project,SCOPES};
