import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root='D:/deepinsight-mini';
process.env.RUNTIME_NODE_MODULES='C:/Users/Admin（无密码）/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/Admin（无密码）/.codex/plugins/cache/openai-primary-runtime/presentations/26.1017.11052/skills/presentations';
const runtimePython='C:/Users/Admin（无密码）/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const out=path.join(root,'output/slides');
await fs.mkdir(out,{recursive:true});
const pres=Presentation.create({slideSize:{width:1280,height:720}});
const navy='#14263D',teal='#168780',ink='#263445',muted='#607083',bg='#F5F7FA';
function box(slide,x,y,w,h,fill){return slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});}
function text(slide,value,x,y,w,h,size=26,color=ink,bold=false){const s=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});s.text=value;s.text.style={fontSize:size,typeface:'Segoe UI',color,bold,insets:0,verticalAlignment:'top',autoFit:'none',wrap:'square'};return s;}
function slide(title,sub){const s=pres.slides.add();s.background.fill='#FFFFFF';box(s,64,46,45,5,teal);text(s,title,64,77,1148,108,43,navy,true);if(sub)text(s,sub,64,184,1130,62,23,muted);return s;}
function footer(s,n,caption='London Office Intelligence | DeepInsight Mini | PoC review, 19 October 2026'){text(s,caption,64,665,1100,24,13,muted);text(s,String(n),1170,660,45,28,18,muted);}

{
 const s=slide('Market information is published.\nYour team still has to find it.','The business challenge: turn scattered updates into a traceable daily view.');
 const cols=[['Scattered sources','Research reports, public planning notices and announcements arrive on different schedules.'],['Unclear change','A newly found document may describe an old event. A revised web page may contain no new market fact.'],['Difficult comparisons','Rent, vacancy and supply figures can use different periods, boundaries and definitions.']];
 cols.forEach((c,i)=>{const x=64+i*395;box(s,x,295,355,3,i===1?teal:'#dce3e9');text(s,c[0],x,324,350,50,28,navy,true);text(s,c[1],x,389,340,155,24,ink);});
 text(s,'Asset managers need a briefing they can check, share and follow up.',64,572,1100,60,29,teal,true);footer(s,1);
 s.speakerNotes.text='Audience: asset managers and business operations. Qualitative workflow problem, not measured time savings or ROI. This is a working PoC, with live AI currently blocked by official DeepSeek HTTP 402. Requirement: docs/USER_REQUEST.txt.';
}
{
 const s=slide('Meet London Office Intelligence','A focused research assistant built around monitoring and a saved briefing.');
 text(s,'Check the market',64,287,420,45,28,navy,true);text(s,'Collect registered public sources and compare them with the previous check.',64,337,390,85,24);
 text(s,'Read a source-backed briefing',64,449,420,48,28,navy,true);text(s,'See what changed, what needs review and which evidence is still missing.',64,501,390,90,24);
 s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'output/screenshots/overview-viewport.png'))),contentType:'image/png',alt:'Actual running product overview with explicit AI quota warning',fit:'contain',position:{left:490,top:270,width:728,height:378}});
 footer(s,2);s.speakerNotes.text='Actual product screenshot from http://127.0.0.1:8766. Captured by tools/capture_final.py. The visible quota warning is intentional: monitoring/reporting success does not imply successful live AI.';
}
{
 const s=slide('Continuous monitoring, with evidence gates','Morning at 08:00 and evening at 18:00, London time. The website can be closed.');
 const stages=[['Check sources','Public pages and RSS'],['Compare history','Body versions and events'],['Validate evidence','Approval before figures'],['Deliver briefing','HTML, PDF and email']];
 stages.forEach((a,i)=>{const x=64+i*298;box(s,x,304,260,125,i===2?navy:bg);text(s,a[0],x+18,327,225,38,25,i===2?'#FFFFFF':navy,true);text(s,a[1],x+18,379,225,40,18,i===2?'#d7e4ed':muted);if(i<3){s.shapes.add({geometry:'rightArrow',position:{left:x+268,top:350,width:24,height:23},fill:teal,line:{fill:'none',width:0}});}});
 text(s,'No new source version?',64,485,500,45,28,navy,true);text(s,'Publish an honest short update. Skip unnecessary model analysis.',64,538,510,90,24);
 text(s,'A source failed?',685,485,500,45,28,navy,true);text(s,'Show partial coverage. Never label a failed check as an unchanged market.',685,538,510,90,24);
 footer(s,3);s.speakerNotes.text='Implementation: app/skills/monitor.py, app/services/scheduler.py, deployment/windows/. Actual Windows Task Scheduler controlled run persisted as 838a1f352ab947e4a788094b1967a4fc, trigger morning, SUCCESS, report f5802561f63e4375bef7cdb908538b49. Daily unattended 08:00/18:00 execution has not yet been observed over multiple days. External notification delivery is disabled.';
}
{
 const s=slide('A planning approval becomes a reviewable source','Live example: the City of London announcement for the Silk Street office scheme.');
 s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'output/screenshots/planning-viewport.png'))),contentType:'image/png',alt:'Actual source evidence view for City of London Silk Street planning announcement',fit:'contain',position:{left:64,top:262,width:730,height:380}});
 text(s,'Verified source',830,280,360,45,27,teal,true);text(s,'Publisher, original link, publication date and retained content hash.',830,332,355,106,24);
 text(s,'Business follow-up',830,455,360,44,27,navy,true);text(s,'Check the project milestone and location. Approval is not completed office supply.',830,505,355,125,24);
 footer(s,4);s.speakerNotes.text='Primary source: https://news.cityoflondon.gov.uk/city-of-london-corporation-approves-major-office-scheme-on-silk-street/ . The announcement predates this PoC; discovery is not a new event today. Supplemental research source: https://www.savills.com/research_articles/255800/393427-0 . Its explicit article time field gives 6 August 2026; metadata extraction was corrected with an audit receipt. No unapproved numeric market claims are shown.';
}
{
 const s=slide('A useful briefing workflow. Clear PoC boundaries.','Business value comes from a repeatable check and a visible path back to the source.');
 const rows=[['Available now','Public-source collection, 101 source-reported observations, chat history and HTML/PDF briefings.'],['Verified in isolation','Scheduled Windows execution and real loopback SMTP acceptance with duplicate suppression.'],['Still blocked','Live AI and actual tool calling: official DeepSeek returned HTTP 402. External delivery is not configured.'],['Next steps','Restore official quota, review the candidate figures, expand submarket coverage and authorize recipient tests.']];
 rows.forEach((r,i)=>{const y=278+i*88;box(s,64,y+4,5,62,i===2?'#D97757':teal);text(s,r[0],88,y,295,55,25,navy,true);text(s,r[1],400,y,792,76,23,ink);});
 footer(s,5);s.speakerNotes.text='Acceptance evidence: output/evidence/G0-model-smoke.json; output/evidence/browser/acceptance.json; output/evidence/smtp/receipt.json; SQLite monitor_runs/schedule_slots. Actual browser six questions remain BLOCKED for real AI and do not count as live agent success. Current retained data includes 101 pending observations, 21 dashboard series, 7 accessible endpoints across Savills, City of London, Bank of England and ONS. Source-reported dashboard figures are distinct from approved quantitative reports. No fabricated market trend chart or ROI is claimed. Dedicated Canary Wharf/Midtown, hybrid-working and wider broker coverage remain incomplete. VPS instructions are supplied, but no remote production deployment is claimed.';
}

for(const [i,s] of pres.slides.items.entries()){
 const blob=await pres.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(out,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await fs.writeFile(path.join(root,'output/slide-build/deck.proto.json'),JSON.stringify(pres.toProto()));
const candidate=path.join(root,'output/slide-build/candidate.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(out,process.env.MINI_DECK_NAME||'London_Office_Intelligence_Business_Demo_v2.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
 pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:5,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:['Segoe UI']},verifyArtifactToolImport:true,
 receiptPath:path.join(root,'output/slide-build',path.basename(finalPath)+'.validation.json')});
console.log(JSON.stringify(result));
