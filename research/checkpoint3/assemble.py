import csv
import json
import pathlib
import re
import concurrent.futures
import requests

root = pathlib.Path(__file__).parent
sources = []
for name in ['direct_literature', 'existing_fulltexts', 'additional_fulltexts']:
    sources.extend(json.loads((root / 'results' / (name + '.json')).read_text())['sources'])
main = [s for s in sources if s['id'] not in ['Gift2015', 'PriceRemerStone2012']]
supp = [s for s in sources if s not in main]
def stringify(x):
    return ' '.join(x) if isinstance(x, list) else str(x)
def url(s):
    return s.get('primary_url', s.get('doi_or_stable_primary_url', ''))
def fetchmeta(s):
    u=url(s)
    if 'doi.org/' not in u:return s['id'], {}
    try:
        r=requests.get('https://api.crossref.org/works/'+u.split('doi.org/')[1], timeout=20)
        return s['id'],r.json().get('message',{}) if r.ok else {}
    except Exception:return s['id'],{}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    metadata=dict(pool.map(fetchmeta,sources))
fallback = {
 'Gong2022': ([('Gong','Hua')], 'Journal of Sports Economics','23','7','950–975'),
 'Sors-2019': ([('Sors','Fabrizio'),('Tomé Lourido','David'),('Parisi','Vittoria'),('Santoro','Ilaria'),('Galmonte','Alessandra'),('Agostini','Tiziano'),('Murgia','Mauro')], 'Frontiers in Psychology','10','','2380'),
 'sabag2023': ([('Sabag','E.'),('Lidor','R.'),('Arnon','M.'),('Morgulev','E.'),('Bar-Eli','M.')], 'Journal of Human Kinetics','89','','313–326'),
 'wang2025': ([('Wang','R.'),('Chen','L.'),('Wu','Y.'),('Zhang','Q.')], 'Frontiers in Psychology','16','','1682389'),
 'ziv2020': ([('Ziv','G.'),('Lidor','R.'),('Zach','S.'),('Brams','S.'),('Helsen','W. F.')], 'Frontiers in Sports and Active Living','2','','572891'),
 'PriceRemerStone2012': ([('Price','Joseph'),('Remer','Marc'),('Stone','Daniel F.')], 'Journal of Economics & Management Strategy','21','1','271–300'),
 'AndersonPierce2009': ([('Anderson','Kyle J.'),('Pierce','David A.')], 'Journal of Sports Sciences','27','7','687–694'),
 'Deutscher2015': ([('Deutscher','Christian')], 'Journal of Sports Analytics','1','2','91–96'),
 'Gift2015': ([('Gift','Paul')], 'Economic Inquiry','53','2','1259–1274'),
 'Pelechrinis-2023': ([('Pelechrinis','Konstantinos')], 'Scientific Reports','13','','4664'),
 'Morgulev-2018': ([('Morgulev','Elia'),('Azar','Ofer H.'),('Lidor','Ronnie'),('Sabag','Eran'),('Bar-Eli','Michael')], 'Frontiers in Psychology','9','','2637'),
 'Cervone-2016-preprint': ([('Cervone','Daniel'),('D’Amour','Alex'),('Bornn','Luke'),('Goldsberry','Kirk')], 'Journal of the American Statistical Association','111','514','585–599'),
 'gomez2020': ([('Gomez-Gonzalez','Carlos'),('Dietl','Helmut'),('Nesseler','Cornel')], 'Frontiers in Psychology','11','','566684'),
 'shu2026': ([('Shu','F.'),('Zhang','L.'),('Xu','X.'),('Xu','R.')], 'PLOS One','21','2','e0342151'),
}
for s in sources:
    if s['id'] in fallback and not metadata[s['id']].get('author'):
        aa,j,v,iss,p=fallback[s['id']]
        metadata[s['id']]={'author':[{'family':f,'given':g} for f,g in aa], 'container-title':[j], 'volume':v,'issue':iss,'page':p,'DOI':url(s).split('doi.org/')[-1]}
(root/'source_metadata.json').write_text(json.dumps(metadata,indent=2))
intro='# Indigo Research: Annotated Bibliography\n\nRyan Kalfus | 22 October 2026\n\nCitation style: APA 7 (working choice for Joe to confirm).\n\nResearch question: Does recent defensive-foul history improve prediction of a counted defensive foul on the next NBA possession beyond the game context already known?\n\nThis follows the supplied Indigo template. The 13 main entries have AI-assisted full-text analysis with methods, findings, limitations, and page or section references. Two abstract-only sources are supplementary and do not count toward the completed full-text analyses. Ryan should review and explain the annotations before submitting them as his work. PDF page numbers refer to the downloaded version unless printed journal pages are identified.\n\n'
parts=[intro]
notes=['# Source analysis notes\n\nPrepared with AI assistance. These notes distinguish paper findings from implications for WMI. Read the cited pages to check and discuss the argument.\n\n']
ris=[]
tracker=[]
for i,s in enumerate(main+supp,1):
    pdf=s.get('local_pdf_path');exists=bool(pdf and pathlib.Path(pdf).exists())
    label='Source '+str(i) if s in main else 'Supplementary source '+str(i-len(main))+' (abstract only)'
    keys=s.get('keywords',['basketball','foul sequences','game context'])
    parts.append('## '+label+'\n\nArticle Citation: '+s['apa_citation']+'\n\nDatabase URL: '+url(s)+'\n\nKeywords: '+', '.join(keys)+'\n\nWere you able to download a PDF of this? '+('Yes — '+pathlib.Path(pdf).name if exists else 'No — full text read online' if s in main else 'No')+'\n\nMain idea and intended use (2–3 sentences): '+s['indigo_annotation']+'\n\n')
    notes.append('## '+label+': '+s['apa_citation']+'\n\nAccess: '+s['full_text_access']+'\n\nMethods and sample: '+stringify(s['method_and_sample'])+'\n\nFindings: '+stringify(s['actual_findings'])+'\n\nLimitations: '+stringify(s['limitations'])+'\n\nUse in WMI: '+s.get('relevance_to_wmi',s.get('relevance_to_WMI',''))+'\n\nEvidence locations:\n'+''.join('- '+x+'\n' for x in s['evidence_locations'])+'\n')
    m=metadata[s['id']];authors=m.get('author',[])
    title=(m.get('title') or [s['apa_citation'].split('). ',1)[-1].split('. ')[0]])[0]
    if 'Sicilia' in s['id']:
        title='DeepHoops: Evaluating Micro-Actions in Basketball Using Deep Feature Representations of Spatio-Temporal Data'
        authors=[{'given':'Anthony','family':'Sicilia'},{'given':'Konstantinos','family':'Pelechrinis'},{'given':'Kirk','family':'Goldsberry'}]
    year=re.search(r'\((\d{4})\)',s['apa_citation']).group(1)
    r=['TY  - JOUR' if m else 'TY  - RPRT','TI  - '+title]
    r+=['AU  - '+a.get('family','')+', '+a.get('given','') for a in authors]
    r+=['PY  - '+year,'UR  - '+url(s)]
    if m.get('DOI'):r+=['DO  - '+m['DOI']]
    for tag,field in [('JO','container-title'),('VL','volume'),('IS','issue'),('SP','page')]:
        v=m.get(field)
        if v:r.append(tag+'  - '+(v[0] if isinstance(v,list) else v))
    r+=['KW  - WMI Checkpoint 3','N1  - '+s['indigo_annotation'],'N1  - Methods: '+stringify(s['method_and_sample']),'N1  - Findings: '+stringify(s['actual_findings']),'N1  - Limits: '+stringify(s['limitations']),'N1  - Evidence: '+ '; '.join(s['evidence_locations'])]
    if exists:r+=['L1  - '+pathlib.Path(pdf).as_uri()]
    ris.append('\n'.join(r+['ER  - ','']))
    tracker.append({'source':s['id'],'citation':s['apa_citation'],'url':url(s),'pdf_downloaded':exists,'full_text_analyzed_by_ai':s in main,'reviewed_by_ryan':False,'locations':'; '.join(s['evidence_locations'])})
synthesis='''## Synthesis and use in the paper

Anderson–Pierce and Shu motivate a sequence question and score/foul-state controls, but their called-event samples answer which team receives a foul conditional on a call. WMI prediction must also include possessions without fouls. Gong, Deutscher, and Pelechrinis show why correctness requires a different outcome and a defensible denominator; their selected late-game evidence cannot label every possession in the WMI dataset. Their different results also argue against assuming a universal home or crowd effect.

Morgulev, Sors, Sabag, and Wang illustrate how event selection, perception, anxiety, and positioning can change a referee study. These mechanisms are largely unobserved in play-by-play, so the paper should report sequence associations without naming an identified psychological cause. Wang's internal inconsistencies make it weak support for precise numerical claims. The women's basketball study offers contextual and exposure controls but includes final-game variables that must not enter prospective predictions; the gaze review supplies indirect methodological caution rather than NBA evidence.

Cervone supplies a conditional-information framework but excludes foul possessions. DeepHoops explicitly models foul outcomes, although its downsampling and tracking requirements prevent a direct performance comparison with WMI. Together these sources support the project's contribution: a transparent descriptive game score paired with a chronological, matched-model test of whether past fouls add information beyond observable context. The literature supports an empirical question; it does not establish that WMI measures referee bias.

Suggested paper structure: introduction and gap; definitions and reconstruction; WMI decomposition; matched prediction design and results; intervening-foul and late-strategy sensitivities; limitations and conclusion. Cite the direct sequence studies in the introduction, reviewed-call studies in the identification limits, and possession models in the prediction methods.
'''
parts.append(synthesis)
(root/'annotated_bibliography.md').write_text(''.join(parts))
(root/'source_analysis_notes.md').write_text(''.join(notes))
(root/'WMI-Checkpoint-3.ris').write_text('\n'.join(ris))
with (root/'source_tracker.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=tracker[0]);w.writeheader();w.writerows(tracker)
print('Main full-text analyses:',len(main),'Supplementary:',len(supp),'PDFs:',sum(r['pdf_downloaded'] for r in tracker))
