#!/usr/bin/env python3
"""Materialize 5,000 source-traceable Snowflake certification questions and solutions per exam."""
from __future__ import annotations
import argparse, hashlib, json, random, re, shutil
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/"data"/"question-banks"
CATALOG=BANK/"generator"/"concepts.v1.json"
BLUEPRINT=BANK/"blueprints"/"2026-10-07.json"
TARGETS=BANK/"coverage"/"authoring-targets.5000.json"
CERTS=BANK/"certifications.json"
OUT=BANK/"generated"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
C=load(CATALOG); CONCEPTS=C["concepts"]; POOLS=C["pools"]; TARGET=int(C["target"]); AS_OF=C["as_of"]
CONTEXTS=[tuple(x) for x in C["contexts"]]; CONSTRAINTS=[tuple(x) for x in C["constraints"]]
ENV=C["env_scales"]; WORK=C["workload_patterns"]; CTRL=C["control_profiles"]
ARCH=["scenario","architecture_decision","troubleshooting","single_select","distinction","operational"]
DIFF=["foundation","exam","advanced"]
TYPE={"scenario":"scenario","architecture_decision":"architecture_decision","troubleshooting":"troubleshooting","single_select":"single_select","distinction":"single_select","operational":"scenario"}
SQLISH={"variant","flatten","qualify","window_functions","pivot","unpivot","match_recognize","period","udf","stored_proc","copy_into"}
ARCHISH={"virtual_warehouse","multi_cluster","replication","secure_sharing","dynamic_tables","snowpipe_streaming","iceberg","delta_direct","openflow","workday_zero_copy","spcs"}
TROUBLE={"query_profile","resource_monitor","streams_view","streaming_monitor","trust_center","access_history","model_monitoring"}

def rng(*parts):
    return random.Random(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:16],16))
def official_source(concept):
    return {"type":"official_announcement" if concept.get("release") else "official_docs",
            "title":concept["label"],"url":concept["source"],"section":None}
def existing(kind):
    rows=[]
    for p in BANK.glob(f"**/{kind}*.jsonl"):
        if OUT in p.parents: continue
        for raw in p.read_text(encoding="utf-8").splitlines():
            if raw.strip(): rows.append(json.loads(raw))
    return rows
def distractors(cid,r):
    cat=CONCEPTS[cid]["category"]
    same=[x for x,v in CONCEPTS.items() if x!=cid and v["category"]==cat]
    rest=[x for x in CONCEPTS if x!=cid and x not in same]
    r.shuffle(same); r.shuffle(rest); return (same+rest)[:3]
def feature_options(cid,ds,r):
    items=[("CORRECT",CONCEPTS[cid]["label"])]+[(d,CONCEPTS[d]["label"]) for d in ds]
    r.shuffle(items); opts=[]; ans=[]; mp={}
    for k,(ident,text) in zip("ABCD",items):
        opts.append({"key":k,"text":text}); mp[k]=ident
        if ident=="CORRECT": ans.append(k)
    return opts,ans,mp
def property_options(cid,ds,r):
    c=CONCEPTS[cid]
    items=[("CORRECT",c["fact"])]+[(d,f"{c['label']} is primarily used to {CONCEPTS[d]['purpose']}.") for d in ds]
    r.shuffle(items); opts=[]; ans=[]; mp={}
    for k,(ident,text) in zip("ABCD",items):
        opts.append({"key":k,"text":text}); mp[k]=ident
        if ident=="CORRECT": ans.append(k)
    return opts,ans,mp
def prompt(arch,c,ctx,constraint,serial):
    scale=ENV[serial%len(ENV)]
    workload=WORK[(serial//len(ENV))%len(WORK)]
    control=CTRL[(serial//(len(ENV)*len(WORK)))%len(CTRL)]
    detail=f"The environment is {scale}, has {workload}, and operates with {control}."
    forms={
      "scenario":[
        "{ctx} needs to {need} and also wants to {constraint}. Which Snowflake capability best fits?",
        "For {ctx}, the requirement is to {need} while trying to {constraint}. What should the team use?",
        "{ctx} is redesigning a workflow to {need}. The design should also {constraint}. Which option is most appropriate?"],
      "architecture_decision":[
        "An architect for {ctx} must {need} while ensuring the design can {constraint}. Which Snowflake capability is the best architectural choice?",
        "{ctx} is comparing Snowflake design options. The chosen design must {need} and {constraint}. Which capability should be selected?",
        "Which Snowflake capability should {ctx} choose when the architecture must {need} and {constraint}?"],
      "troubleshooting":[
        "{ctx} is struggling to {need}. The team also needs to {constraint}. Which Snowflake capability should be evaluated first?",
        "A production issue prevents {ctx} from being able to {need}. Which Snowflake capability most directly addresses the problem while helping to {constraint}?",
        "{ctx} sees an operational gap around the need to {need}. Which capability is the most direct corrective action?"],
      "single_select":["Which statement about {label} is correct?","Which option most accurately describes {label}?","What is the primary Snowflake purpose of {label}?"],
      "distinction":[
        "{ctx} is deciding whether {label} or a neighboring Snowflake capability applies. Which option correctly identifies what {label} is designed to do?",
        "Which description correctly distinguishes {label} from adjacent Snowflake features?",
        "For {ctx}, which statement correctly characterizes {label}?"],
      "operational":[
        "{ctx} needs an operational mechanism to {need}, with an emphasis on the ability to {constraint}. Which capability should be used?",
        "Which Snowflake capability gives {ctx} the most direct operational path to {need} while helping to {constraint}?",
        "{ctx} wants to operationalize a process that must {need}. Which feature best satisfies that requirement?"]}
    base=forms[arch][serial%3].format(ctx=ctx,need=c["need"],constraint=constraint,label=c["label"])
    return f"{detail} {base}"
def qtype(arch,cid):
    if cid in SQLISH and arch in {"scenario","troubleshooting","single_select","distinction"}: return "sql_reasoning"
    if cid in ARCHISH and arch in {"architecture_decision","scenario"}: return "architecture_decision"
    if cid in TROUBLE and arch in {"troubleshooting","operational"}: return "troubleshooting"
    return TYPE[arch]
def build(code,cert_id,obj,cid,serial,ordinal):
    c=CONCEPTS[cid]; r=rng(code,obj,cid,str(serial),str(ordinal))
    arch=ARCH[(serial+ordinal)%len(ARCH)]
    ctx_id,ctx=CONTEXTS[(serial*7+ordinal*3)%len(CONTEXTS)]
    con_id,con=CONSTRAINTS[(serial*5+ordinal*11)%len(CONSTRAINTS)]
    ds=distractors(cid,r)
    opts,ans,mp=(property_options(cid,ds,r) if arch in {"single_select","distinction"} else feature_options(cid,ds,r))
    qid=f"{code}-{serial:04d}"
    source=[official_source(c)]
    q={"id":qid,"certification_id":cert_id,"exam_code":code,"blueprint_domain":None,
       "blueprint_objective":obj,"topic":c["label"],"subtopic":cid.replace("_"," "),
       "question_type":qtype(arch,cid),"difficulty":DIFF[(serial+ordinal)%3],
       "prompt":prompt(arch,c,ctx,con,serial),"options":opts,"answer_key":ans,"sources":source,
       "as_of":AS_OF,"lifecycle_note":c.get("lifecycle"),"status":"draft",
       "tags":["generated-v1",f"concept:{cid}",f"context:{ctx_id}",f"constraint:{con_id}",f"archetype:{arch}",
               f"source-class:{'release-aware' if c.get('release') else 'durable'}"]}
    da=[]
    for o in opts:
        if o["key"] in ans: continue
        d=CONCEPTS[mp[o["key"]]]
        why=(f"This statement assigns {d['label']}'s purpose to {c['label']}. {d['label']} is primarily used to {d['purpose']}."
             if arch in {"single_select","distinction"} else
             f"{d['label']} is primarily used to {d['purpose']}; it does not directly satisfy the requirement to {c['need']}.")
        da.append({"key":o["key"],"why_wrong":why})
    s={"question_id":qid,"certification_id":cert_id,"exam_code":code,"answer_key":ans,
       "explanation":c["fact"],
       "reasoning":f"In this scenario, {ctx} needs to {c['need']}. {c['label']} directly addresses that requirement. The additional design goal is to {con}, which does not change the underlying feature selection.",
       "distractor_analysis":da,
       "exam_trap":f"Do not choose an adjacent feature merely because it appears in the same Snowflake domain. Anchor the decision on the requirement to {c['need']}.",
       "code_example":None,"sources":source,"as_of":AS_OF,"status":"draft"}
    return q,s
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--clean",action="store_true"); ap.add_argument("--artifact-summary"); a=ap.parse_args()
    if a.clean and OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True,exist_ok=True)
    bp={x["exam_code"]:x for x in load(BLUEPRINT)["certifications"]}
    targ=load(TARGETS)["exams"]; cert_by_code={x["code"]:x["id"] for x in load(CERTS)["certifications"]}
    eq=defaultdict(list); es=defaultdict(list)
    for x in existing("questions"): eq[x["exam_code"]].append(x)
    for x in existing("solutions"): es[x["exam_code"]].append(x)
    summary={"as_of":AS_OF,"target_per_exam":TARGET,"generator":"scripts/generate_question_banks_5000.py","exams":{}}
    for code,b in bp.items():
        if len(eq[code])!=len(es[code]): raise SystemExit(f"{code}: existing Q/S mismatch")
        alloc=targ[code]["allocations"]; pools=POOLS[code]
        if len(alloc)!=len(pools): raise SystemExit(f"{code}: objective/pool mismatch")
        remaining=TARGET-len(eq[code]); existing_ids={q["id"] for q in eq[code]}
        nums=[int(m.group(1)) for i in existing_ids if (m:=re.match(rf"^{re.escape(code)}-(\d+)$",i))]
        serial=max(nums,default=0)+1
        total=sum(x["target"] for x in alloc); raw=[remaining*x["target"]/total for x in alloc]; counts=[int(x) for x in raw]
        for i in sorted(range(len(raw)),key=lambda j:raw[j]-counts[j],reverse=True)[:remaining-sum(counts)]: counts[i]+=1
        qs=[]; ss=[]; rel=dur=0
        for oi,(al,n) in enumerate(zip(alloc,counts)):
            obj=al["objective"]; pool=pools[oi]; durable=[x for x in pool if not CONCEPTS[x].get("release")] or pool
            release=[x for x in pool if CONCEPTS[x].get("release")]
            for ordinal in range(n):
                use=bool(release) and rel<750 and ((ordinal+oi)%8==0); source=release if use else durable
                cid=source[(ordinal*5+oi*3)%len(source)]
                while f"{code}-{serial:04d}" in existing_ids: serial+=1
                q,s=build(code,cert_by_code[code],obj,cid,serial,ordinal); qs.append(q); ss.append(s)
                rel+=bool(CONCEPTS[cid].get("release")); dur+=not bool(CONCEPTS[cid].get("release"))
                existing_ids.add(q["id"]); serial+=1
        d=OUT/code; d.mkdir(parents=True,exist_ok=True)
        (d/"questions.generated.jsonl").write_text("".join(json.dumps(x,separators=(",",":"),ensure_ascii=False)+"\n" for x in qs),encoding="utf-8")
        (d/"solutions.generated.jsonl").write_text("".join(json.dumps(x,separators=(",",":"),ensure_ascii=False)+"\n" for x in ss),encoding="utf-8")
        info={"existing_questions":len(eq[code]),"generated_questions":len(qs),"total_questions":len(eq[code])+len(qs),
              "existing_solutions":len(es[code]),"generated_solutions":len(ss),"total_solutions":len(es[code])+len(ss),
              "generated_durable":dur,"generated_release_aware":rel}
        if info["total_questions"]!=TARGET or info["total_solutions"]!=TARGET: raise SystemExit(f"{code}: target not met")
        summary["exams"][code]=info
    sp=Path(a.artifact_summary) if a.artifact_summary else OUT/"summary.json"; sp.parent.mkdir(parents=True,exist_ok=True)
    sp.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    for c,i in summary["exams"].items(): print(f"{c}: {i['total_questions']} questions / {i['total_solutions']} solutions")
if __name__=="__main__": main()
