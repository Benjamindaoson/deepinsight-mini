"""Assessment coverage and source-reported observations, separate from approved publication."""
import json
from app.skills.compare import compare

TOPICS = [
    dict(id="rents", title="Prime & Grade A rents", metrics=["prime_rent","grade_a_rent"],
         question="How have prime and Grade A rents changed in the City and West End? Compare only compatible definitions, units and observation periods.", source_targets=["Savills Central London Office Research"], note="Prime, average achieved and Grade A definitions remain distinct."),
    dict(id="vacancy", title="Vacancy & availability", metrics=["vacancy_rate","availability"],
         question="What do the sources report about vacancy and availability across London submarkets, and which periods and definitions are comparable?", source_targets=["Savills supply and vacancy section"], note="A percentage vacancy rate is different from available floor area."),
    dict(id="leasing", title="Leasing take-up & activity", metrics=["take_up","leasing_transactions"],
         question="What is the latest verifiable leasing take-up and transaction activity? Separate quarterly and half-year totals.", source_targets=["Savills leasing summary","City of London Newsroom"], note="Q2 and H1 totals cannot be compared as like-for-like periods."),
    dict(id="pipeline", title="Supply pipeline", metrics=["supply","development_completions","construction_pipeline","prelet_share"],
         question="What new developments, refurbishments and pre-lets affect the supply pipeline? Distinguish application, approval, construction and completion.", source_targets=["Savills development pipeline","City of London planning announcements"], note="Planned, under construction, completed and pre-let are separate milestones."),
    dict(id="submarkets", title="Submarket dynamics", metrics=["prime_rent","vacancy_rate","take_up"],
         question="Compare City, West End, Canary Wharf and Midtown/Fringe using verified sources. Identify missing coverage instead of substituting Central London aggregates.", source_targets=["Savills submarket analysis","City of London planning announcements"], note="Dedicated Canary Wharf and Midtown series are not yet connected."),
    dict(id="macro", title="Macroeconomic influences", metrics=["bank_rate","cpi_inflation","employment_rate","gdp_growth"],
         question="What do official interest-rate, inflation, GDP and employment series show, and how might they influence office demand without proving a change in rents?", source_targets=["Bank of England official Bank Rate","ONS CPI D7G7/MM23","ONS employment LF24/LMS","ONS GDP IHYQ/PN2"], note="UK macro series are context, not London office performance measures."),
    dict(id="demand", title="Occupier demand drivers", metrics=["grade_a_take_up_share","breeam_take_up_share","active_demand"],
         question="What evidence supports flight-to-quality, ESG/sustainability preferences and hybrid-working impacts on London office demand? Separate source facts from interpretation.", source_targets=["Savills take-up and future demand sections"], note="Grade A and BREEAM shares are proxies; no causal hybrid-working effect is claimed."),
    dict(id="events", title="News, risks & opportunities", metrics=[],
         question="Which new leasing, relocation or planning events have been discovered since the previous successful check, and what evidence supports a business risk or opportunity?", source_targets=["City of London Newsroom","Registered institutional announcements"], note="Discovery date and original event/publication date are shown separately."),
]

METRIC_LABELS = dict(prime_rent="Prime rent",grade_a_rent="Grade A rent",vacancy_rate="Vacancy rate",
    availability="Available supply",take_up="Leasing take-up",leasing_transactions="Leasing transactions",
    supply="Available stock",development_completions="Development completions",construction_pipeline="Under construction",
    prelet_share="Pre-let share of scheduled deliveries",grade_a_take_up_share="Grade A share of take-up",
    breeam_take_up_share="BREEAM Excellent/Outstanding share",active_demand="Active occupier demand",
    bank_rate="Official Bank Rate",cpi_inflation="CPI annual inflation",employment_rate="UK employment rate",
    gdp_growth="Real GDP quarterly growth")


def dashboard(store):
    observations = store.query("""SELECT o.*,d.title,d.url,d.published_at,d.source_id,d.status document_status,
        instr(d.text,o.evidence_text)>0 evidence_valid,
        s.status source_health FROM observations o JOIN documents d ON d.id=o.document_id
        JOIN sources s ON s.id=d.source_id WHERE d.status='SOURCE_VERIFIED'
        AND o.review_status NOT IN ('REJECTED','RETRACTED') ORDER BY o.period DESC,o.geography LIMIT 300""")
    for row in observations:
        row["label"] = METRIC_LABELS.get(row["metric"],row["metric"].replace("_"," ").title())
        row["display_value"] = f"{row['value']:,.2f}".rstrip("0").rstrip(".")
    latest = {}
    for row in observations:
        latest.setdefault((row["metric"],row["geography"],row["definition"]),row)
    topics = []
    for original in TOPICS:
        topic = dict(original)
        topic["observations"] = [o for o in latest.values() if o["metric"] in topic["metrics"]]
        topic["coverage"] = "Source figures available" if topic["observations"] else "Evidence gap"
        topics.append(topic)
    submarkets = ["City","West End","Canary Wharf","Midtown / Fringe"]
    matrix = []
    for geography in submarkets:
        rows = [o for o in latest.values() if o["geography"]==geography or (geography=="Midtown / Fringe" and "Fringe" in o["geography"])]
        matrix.append({"geography":geography,"observations":rows,"coverage":"Available" if rows else "No dedicated observations"})
    # Numeric market charts are still gated on actual approval and compatible periods.
    approved_charts = []
    groups = {}
    for obs in observations:
        if obs["review_status"] == "APPROVED" and obs["source_health"] == "HEALTHY":
            key = tuple(obs[k] for k in ("metric","geography","definition","unit","publisher"))
            groups.setdefault(key,[]).append(obs)
    for key, group in groups.items():
        group.sort(key=lambda x:x["period"])
        if len(group)>=2 and all(compare(a,b)["status"]=="COMPARABLE" for a,b in zip(group,group[1:])):
            approved_charts.append({"title":key[1]+" "+METRIC_LABELS.get(key[0],key[0]),"series":group})
    # User-requested raw API visualization is separate from analyst-approved market trend publication.
    # Plot only a single current official series, with explicit source/period/review labels; no computed deltas.
    source_history=[]
    for metric,source_id in (("cpi_inflation","ons_cpi"),("employment_rate","ons_employment"),("gdp_growth","ons_gdp")):
        series=[]
        for o in observations:
            if o['metric']!=metric or o['source_id']!=source_id or o['source_health']!='HEALTHY' or not o['evidence_valid']:
                continue
            try:
                if float(json.loads(o['evidence_text'])['value'])==o['value']:
                    series.append(o)
            except (ValueError,KeyError,TypeError):
                continue
        keys={tuple(o[k] for k in ('definition','unit','publisher','document_id')) for o in series}
        if len(series)>=2 and len(keys)==1 and len({o['period'] for o in series})==len(series):
            source_history.append({'title':METRIC_LABELS[metric], 'series':sorted(series,key=lambda x:x['period']),
                'publisher':series[0]['publisher'],'document_id':series[0]['document_id'],
                'review_status':'Source-reported API history · review pending','url':series[0]['url']})
    return {"topics":topics,"observations":observations,"latest_observations":list(latest.values()),
        "submarkets":submarkets,"submarket_matrix":matrix,"approved_charts":approved_charts,
        "source_history":source_history,
        "coverage_count":sum(bool(t["observations"]) for t in topics),
        "sources":store.query("SELECT id,name,url,status,last_success,error FROM sources")}
